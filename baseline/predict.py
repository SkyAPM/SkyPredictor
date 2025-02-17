#  Copyright 2025 SkyAPM org
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import datetime
import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import pandas as pd
from prometheus_client import Counter, Summary
from prophet import Prophet

from baseline.fetcher import LabelKeyValue, Fetcher, FetchedData

logger = logging.getLogger(__name__)

predict_total_count = Counter('predict_total_count', 'The total number of predict metrics', ['name'])
predict_metrics_count = Counter('predict_metrics_count', 'The number of predict metrics', ['name'])
predict_metrics_total_time = Summary('predict_metrics_total_time', 'The time spent on predict all metrics', ['name'])
predict_metrics_group_metrics_time = Summary('predict_metrics_group_metrics_time', 'The time spent on predict metrics',
                                             ['name'])
predict_metrics_single_time = Summary('predict_metrics_single_time', 'The time spent on predict single metrics',
                                      ['name'])


class PredictConfig:
    def __init__(self, min_days: int, frequency: str, period: int):
        self.min_days = min_days
        self.frequency = frequency
        self.period = period


class ReadyPredictMeter:
    def __init__(self, service_name: str, single_df: Optional[pd.DataFrame] = None,
                 label_dfs: Optional[dict[frozenset[LabelKeyValue], pd.DataFrame]] = None):
        self.service_name = service_name
        self.single_df = single_df
        self.label_dfs = label_dfs


class PredictValue:
    value: int
    upper_value: int
    lower_value: int

    def __init__(self, value: int, upper_value: int, lower_value: int):
        self.value = value
        self.upper_value = upper_value
        self.lower_value = lower_value

    @staticmethod
    def from_dict(d: dict) -> "PredictValue":
        return PredictValue(d["value"], d["upper_value"], d["lower_value"])


class PredictTimestampWithSingleValue:
    timestamp: pd.Timestamp
    value: PredictValue

    def __init__(self, timestamp: pd.Timestamp, value: PredictValue):
        self.timestamp = timestamp
        self.value = value

    @staticmethod
    def from_dict(d: dict) -> "PredictTimestampWithSingleValue":
        return PredictTimestampWithSingleValue(
            pd.Timestamp(d["timestamp"]),
            PredictValue.from_dict(d["value"])
        )


class PredictLabeledWithLabeledValue:
    label: frozenset[LabelKeyValue]
    time_with_values: list[PredictTimestampWithSingleValue]

    def __init__(self, label: frozenset[LabelKeyValue], time_with_values: list[PredictTimestampWithSingleValue]):
        self.label = label
        self.time_with_values = time_with_values

    @staticmethod
    def from_dict(d: dict) -> "PredictLabeledWithLabeledValue":
        label = frozenset(LabelKeyValue.from_dict(l) for l in d["label"])
        time_with_values = [
            PredictTimestampWithSingleValue.from_dict(twv)
            for twv in d["time_with_values"]
        ]
        return PredictLabeledWithLabeledValue(label, time_with_values)


class PredictMeterResult:
    service_name: str
    single: Optional[list[PredictTimestampWithSingleValue]]
    labeled: Optional[list[PredictLabeledWithLabeledValue]]

    def __init__(self, service_name: str, single: Optional[list[PredictTimestampWithSingleValue]] = None,
                 labeled: Optional[list[PredictLabeledWithLabeledValue]] = None):
        self.service_name = service_name
        self.single = single
        self.labeled = labeled

    def filter_time(self, start: pd.Timestamp, end: pd.Timestamp):
        if self.single:
            self.single = [entry for entry in self.single if start <= entry.timestamp <= end]
        if self.labeled:
            for labeled_entry in self.labeled:
                labeled_entry.time_with_values = [
                    entry for entry in labeled_entry.time_with_values if start <= entry.timestamp <= end
                ]

    @staticmethod
    def from_dict(d: dict) -> "PredictMeterResult":
        single, labeled = None, None
        if d.get("single") is not None:
            single = [PredictTimestampWithSingleValue.from_dict(s) for s in d.get("single")]
        if d.get("labeled") is not None:
            labeled = [PredictLabeledWithLabeledValue.from_dict(l) for l in d.get("labeled")]
        return PredictMeterResult(d["service_name"], single, labeled)


def meter_to_result(meter: ReadyPredictMeter, single: Optional[pd.DataFrame] = None,
                    multiple: Optional[dict[frozenset[LabelKeyValue], pd.DataFrame]] = None) -> PredictMeterResult:
    if single is not None:
        data = single[~single['ds'].isin(meter.single_df['ds'])]
        result: list[PredictTimestampWithSingleValue] = []
        for idx, row in data.iterrows():
            result.append(PredictTimestampWithSingleValue(
                timestamp=row['ds'],
                value=PredictValue(value=row['yhat'], upper_value=row['yhat_upper'], lower_value=row['yhat_lower'])
            ))
        return PredictMeterResult(meter.service_name, single=result)
    elif multiple is not None:
        result: list[PredictLabeledWithLabeledValue] = []
        for labels, label_df in meter.label_dfs.items():
            data = multiple[labels][~multiple[labels]['ds'].isin(label_df['ds'])]
            time_with_values: list[PredictTimestampWithSingleValue] = []
            for idx, row in data.iterrows():
                time_with_values.append(PredictTimestampWithSingleValue(
                    timestamp=row['ds'],
                    value=PredictValue(value=ignore_nagative_value(row['yhat']),
                                       upper_value=ignore_nagative_value(row['yhat_upper']),
                                       lower_value=ignore_nagative_value(row['yhat_lower']))
                ))
            result.append(PredictLabeledWithLabeledValue(label=labels, time_with_values=time_with_values))
        return PredictMeterResult(meter.service_name, labeled=result)


def ignore_nagative_value(value: int) -> int:
    return value if value > 0 else 0


class PredictService:

    def __init__(self, fetcher: Fetcher, name: str, conf: PredictConfig):
        self.fetcher = fetcher
        self.name = name
        self.conf = conf
        self.future_max_time = calc_max_predict_time(conf)

    def predict(self) -> list[PredictMeterResult]:
        with predict_metrics_total_time.labels(self.name).time():
            return self.predict0()

    def predict0(self) -> list[PredictMeterResult]:
        predict_total_count.labels(self.name).inc()
        data = self.fetcher.fetch(self.name)
        if data is None:
            logger.info(f"no data fetched for {self.name}")
            return []
        result: list[PredictMeterResult] = []
        with predict_metrics_group_metrics_time.labels(self.name).time():
            metrics = list(self.split_to_meter(data))
        logger.info(f"total {len(metrics)} services in the {self.name} is available to calc baseline")
        start_time = time.perf_counter()
        predict_metrics_count.labels(self.name).inc(len(metrics))

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.process_meter, meter) for idx, meter in enumerate(metrics, 1)]
            for future in futures:
                try:
                    result.append(future.result())
                except Exception as e:
                    logger.error(f"Error processing meter: {e}, stacktrace: {"".join(traceback.format_exception(type(e), e, e.__traceback__))}")
        end_time = time.perf_counter()
        logger.info(f"process {self.name} metrics total use time {end_time - start_time:.6f} seconds")
        return result

    def process_meter(self, meter: ReadyPredictMeter) -> PredictMeterResult:
        with predict_metrics_single_time.labels(self.name).time():
            return self.process_meter0(meter)

    def process_meter0(self, meter: ReadyPredictMeter) -> PredictMeterResult:
        if meter.single_df is not None:
            m = Prophet(daily_seasonality=True, weekly_seasonality=False, yearly_seasonality=False)
            m.fit(meter.single_df)
            future = m.make_future_dataframe(periods=self.calc_future_period(meter.single_df), freq=self.conf.frequency)
            forecast = m.predict(future)
            logger.info(f"Predicted for {meter.service_name} of {self.name} to {future["ds"].max()}")
            return meter_to_result(meter, single=forecast)
        elif meter.label_dfs is not None:
            multiple: dict[frozenset[LabelKeyValue], pd.DataFrame] = {}
            future = None
            for labels, df in meter.label_dfs.items():
                m = Prophet(daily_seasonality=True, weekly_seasonality=False, yearly_seasonality=False)
                m.fit(df)
                future = m.make_future_dataframe(periods=self.calc_future_period(df), freq=self.conf.frequency)
                forecast = m.predict(future)
                multiple[labels] = forecast
            logger.info(f"Predicted for {meter.service_name} of {self.name} to {future["ds"].max()}")
            return meter_to_result(meter, multiple=multiple)

    def calc_future_period(self, df: pd.DataFrame) -> int:
        df_max_time = pd.to_datetime(df['ds'].max())
        future_dates = pd.date_range(start=df_max_time, end=self.future_max_time, freq=self.conf.frequency)
        if len(future_dates) <= 0:
            return self.conf.period
        return len(future_dates)

    def split_to_meter(self, data: FetchedData):
        if data.single is not None:
            service_df = data.df.groupby(data.single.service_name_column)
            saved_column = {
                data.single.timestamp_column: 'ds',
                data.single.value_column: 'y'
            }
            for service_name, service_df in service_df:
                renamed_df = service_df.loc[:, saved_column.keys()].rename(columns=saved_column)
                renamed_df['ds'] = pd.to_datetime(renamed_df['ds'], format=data.single.time_format)
                renamed_df = renamed_df.dropna()
                if len(renamed_df) < self.conf.min_days * 24:  # min hours = min_days * 24 hour
                    logger.info(f"Skipping {service_name}({self.name}), less than {self.conf.min_days} "
                                f"days(needs {self.conf.min_days * 24} count) data points(current: {len(renamed_df)})")
                    continue
                yield ReadyPredictMeter(service_name, renamed_df)
        elif data.multiple is not None:
            service_df = data.df.groupby(data.multiple.service_name_column)
            for service_name, service_df in service_df:
                service_label_df: dict[frozenset[LabelKeyValue], pd.DataFrame] = {}
                for val_conf in data.multiple.value_columns:
                    saved_column = {
                        data.multiple.time_stamp_column: 'ds',
                        val_conf.value: 'y'
                    }
                    renamed_df = service_df.loc[:, saved_column.keys()].rename(columns=saved_column)
                    renamed_df['ds'] = pd.to_datetime(renamed_df['ds'], format=data.multiple.time_format)
                    renamed_df = renamed_df.dropna()
                    if len(renamed_df) < self.conf.min_days * 24:  # min hours = min_days * 24 hour
                        logger.warning("Skipping %s(%s), labels: %s, less than %d data points(current: %d)" %
                                       (service_name, self.name, val_conf.tags, self.conf.min_days, len(renamed_df)))
                        continue
                    service_label_df[frozenset(val_conf.tags)] = renamed_df

                if len(service_label_df) == 0:
                    logger.warning("Skipping %s(%s), no valid (labels) data points" % (service_name, self.name))
                    continue
                yield ReadyPredictMeter(service_name, label_dfs=service_label_df)


def calc_max_predict_time(conf: PredictConfig) -> datetime.datetime:
    freq = conf.frequency.lower()
    if freq == 'd':
        return datetime.datetime.now() + datetime.timedelta(days=conf.period)
    elif freq == 'h':
        return datetime.datetime.now() + datetime.timedelta(hours=conf.period)
    elif freq == 't' or freq == 'm':
        return datetime.datetime.now() + datetime.timedelta(minutes=conf.period)
    elif freq == 's':
        return datetime.datetime.now() + datetime.timedelta(seconds=conf.period)
    elif freq == 'w':
        return datetime.datetime.now() + datetime.timedelta(weeks=conf.period)
    raise ValueError(f"Unknown frequency type: {conf.frequency}")

