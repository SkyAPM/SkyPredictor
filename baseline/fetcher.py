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
import logging
from abc import ABC, abstractmethod
import datetime
from typing import Optional

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

from config.config import BaselineFetchConfig, BaselineFetchMetricsConfig

logger = logging.getLogger(__name__)

max_fetch_data_period = 80

class LabelKeyValue:
    key: str
    value: str

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "%s=%s" % (self.key, self.value)

    @staticmethod
    def from_dict(d: dict) -> "LabelKeyValue":
        return LabelKeyValue(d["key"], d["value"])


class FetchedSingleDataConfig:
    service_name_column: str
    timestamp_column: str
    value_column: str
    time_format: str

    def __init__(self, service_name_column: str, timestamp_column: str, value_column: str, time_format: str):
        self.service_name_column = service_name_column
        self.timestamp_column = timestamp_column
        self.value_column = value_column
        self.time_format = time_format


class FetchedMultipleValueColumnConfig:
    tags: list[LabelKeyValue]
    value: str

    def __init__(self, tags: list[LabelKeyValue], value: str):
        self.tags = tags
        self.value = value


class FetchedMultipleDataConfig:
    service_name_column: str
    time_stamp_column: str
    value_columns: list[FetchedMultipleValueColumnConfig]
    time_format: str

    def __init__(self, service_name_column: str, time_stamp_column: str, value_columns: list[FetchedMultipleValueColumnConfig], time_format: str):
        self.service_name_column = service_name_column
        self.time_stamp_column = time_stamp_column
        self.value_columns = value_columns
        self.time_format = time_format


class FetchedData:
    def __init__(self, df: pd.DataFrame, single: FetchedSingleDataConfig, multiple: FetchedMultipleDataConfig):
        self.df = df
        self.single = single
        self.multiple = multiple


class Fetcher(ABC):

    @abstractmethod
    def metric_names(self) -> list[str]:
        pass

    def ready_fetch(self):
        pass

    @abstractmethod
    def fetch(self, metric_name: str) -> Optional[FetchedData]:
        pass


class GraphQLFetcher(Fetcher):

    def __init__(self, conf: BaselineFetchConfig):
        self.conf = conf
        self.services = None
        self.total_period = None
        self.metrics = {metric.name: metric for metric in conf.metrics}
        self.base_address = conf.server.address if not conf.server.address.endswith("/") else conf.server.address[:-1]

    def metric_names(self) -> list[str]:
        return [meter.name for meter in self.conf.metrics if meter.enabled]

    def ready_fetch(self):
        all_services = set()
        for layer in self.conf.server.layers:
            services = self.fetch_layer_services(layer)
            for service in services:
                all_services.add(service)
        self.services = all_services
        self.total_period = self.query_need_period()

    def fetch(self, metric_name: str) -> Optional[FetchedData]:
        if self.services is None or len(self.services) == 0:
            return None
        meter_conf = self.metrics[metric_name]
        if not meter_conf.enabled:
            return None
        fetch_data = None
        for (service, normal) in self.services:
            fetch_data = self.fetch_service_metrics(service, normal, metric_name, fetch_data)
        return fetch_data

    def fetch_service_metrics(self, service_name: str, normal: bool, metric_name: str, prev_data: FetchedData) -> FetchedData:
        count = 0
        for start, end in self.generate_time_buckets():
            prev_data, per_count = self.fetch_service_metrics_with_rangs(service_name, normal, metric_name, prev_data, start, end)
            count += per_count
        logger.info(f"Total fetched {count} data points for {metric_name}(service: {service_name})")
        return prev_data

    def fetch_service_metrics_with_rangs(self, service_name: str, normal: bool, metric_name: str,
                                         prev_data: FetchedData, start: str, end: str) -> tuple[FetchedData, int]:
        payload = {
            "query": """
                query MetricsQuery($duration: Duration!) {
                    result: execExpression(
                        expression: "view_as_seq(%s)\"
                        entity: {
                            serviceName: "%s"
                            normal: %s
                        }
                        duration: $duration
                    ) {
                        results {
                            metric {
                                labels { key value }
                            }
                            values { id value }
                        }
                    }
                }
            """ % (metric_name, service_name, str(normal).lower()),
            "variables": {"duration": {
                "start": start,
                "end": end,
                "step": self.conf.server.down_sampling,
            }}
        }

        results = self.fetch_data(f"{self.base_address}/graphql", payload)['result']['results']
        if len(results) == 0:
            return prev_data, 0

        if prev_data is None:
            df = pd.DataFrame()
            single, multiple = None, None
            if len(results) == 1 and len(results[0]['metric']['labels']) == 0:
                single = FetchedSingleDataConfig(
                    service_name_column="svc",
                    timestamp_column="ts",
                    value_column="value",
                    time_format=self.query_metric_time_format())
            else:
                value_columns = []
                for inx, result in enumerate(results):
                    value_columns.append(FetchedMultipleValueColumnConfig(
                        tags=[LabelKeyValue(label['key'], label['value']) for label in result['metric']['labels']],
                        value="label_%d" % inx))
                multiple = FetchedMultipleDataConfig(
                    service_name_column="svc",
                    time_stamp_column="ts",
                    value_columns=value_columns,
                    time_format=self.query_metric_time_format())
            prev_data = FetchedData(df, single, multiple)

        min_date = None
        max_date = None
        count = 0
        if prev_data.single is not None:
            df = prev_data.df
            for result in results:
                for val in result['values']:
                    if val['value'] is None:
                        continue
                    max_date = self.convert_metric_time(int(val['id']))
                    if min_date is None:
                        min_date = max_date
                    row = {
                        prev_data.single.service_name_column: service_name,
                        prev_data.single.timestamp_column: max_date,
                        prev_data.single.value_column: int(val['value'])
                    }
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                    count += 1
            prev_data.df = df
            logger.info(f"Fetched {count} data points for {metric_name}(service: {service_name}) from {min_date} to {max_date}")
            return prev_data, count
        elif prev_data.multiple is not None:
            df = prev_data.df
            for val_inx, values in enumerate(results[0]['values']):
                cur_date = self.convert_metric_time(int(values['id']))

                row = {prev_data.multiple.service_name_column: service_name,
                       prev_data.multiple.time_stamp_column: max_date}
                has_value = False
                for inx, result in enumerate(results):
                    for _ in result['metric']['labels']:
                        val = results[inx]['values'][val_inx]['value']
                        if val is None:
                            continue
                        max_date = cur_date
                        if min_date is None:
                            min_date = max_date
                        row["label_%d" % inx] = int(val)
                        has_value = True
                if has_value:
                    df = pd.concat([df, pd.DataFrame([row])])
                    count += 1
            prev_data.df = df
            logger.info(f"Fetched {count} data points for {metric_name}(service: {service_name}) from {min_date} to {max_date}")

        return prev_data, count

    def fetch_layer_services(self, layer: str) -> list[tuple[str, bool]]:
        payload = {
            "query": """
                query queryServices($layer: String!) {
                    services: listServices(layer: $layer) {
                        label: name
                        normal
                    }
                }
            """,
            "variables": {"layer": layer}
        }

        services = self.fetch_data(f"{self.base_address}/graphql", payload)['services']
        names = []
        for service in services:
            names.append((service['label'], bool(service['normal'])))
        return names

    def query_need_period(self) -> int:
        resp = self.fetch_get_data(f"{self.base_address}/status/config/ttl")
        total_days = int(resp['metrics']['day'])
        sampling = self.conf.server.down_sampling.lower()
        if sampling == 'hour':
            return total_days * 24
        elif sampling == 'minute':
            return total_days * 24 * 60
        raise Exception("Unsupported down sampling: %s" % sampling)

    def generate_time_buckets(self) -> list[tuple[str, str]]:
        end_time = datetime.datetime.now()
        sampling = self.conf.server.down_sampling.lower()
        if sampling == 'hour':
            start_time = end_time - datetime.timedelta(hours=self.total_period)
            return self.generate_time_buckets_by_range(start_time, end_time, self.delta_hour, '%Y-%m-%d %H')
        elif sampling == 'minute':
            start_time = end_time - datetime.timedelta(minutes=self.total_period)
            return self.generate_time_buckets_by_range(start_time, end_time, self.delta_minute, '%Y-%m-%d %H%M')
        raise Exception("Unsupported down sampling: %s" % sampling)

    def generate_time_buckets_by_range(self, start, end, delta, formate) -> list[tuple[str, str]]:
        cur_end_time = start + delta(max_fetch_data_period - 1)
        if cur_end_time > end:
            return [start.strftime(formate), end.strftime(formate)]
        results = []
        while start < cur_end_time < end:
            results.append([start.strftime(formate), cur_end_time.strftime(formate)])
            start = cur_end_time + delta(1)
            cur_end_time += delta(max_fetch_data_period)
        if start < end:
            results.append((start.strftime(formate), end.strftime(formate)))
        return results

    def delta_hour(self, val):
        return datetime.timedelta(hours=val)

    def delta_minute(self, val):
        return datetime.timedelta(minutes=val)

    def query_metric_time_format(self) -> str:
        sampling = self.conf.server.down_sampling.lower()
        if sampling == 'hour':
            return '%Y%m%d%H'
        elif sampling == 'minute':
            return '%Y%m%d%H%M'
        raise Exception("Unsupported down sampling: %s" % sampling)

    def convert_metric_time(self, val_id: int) -> str:
        return datetime.datetime.fromtimestamp(val_id / 1000).strftime(self.query_metric_time_format())

    def fetch_get_data(self, url):
        if self.conf.server.username and self.conf.server.password:
            auth = HTTPBasicAuth(self.conf.server.username, self.conf.server.password)
        else:
            auth = None

        response = requests.get(url, auth=auth, headers={"Accept": "application/json"})
        if response.status_code != 200:
            raise Exception("Failed to fetch data from GraphQL: %s" % response.text)
        return response.json()

    def fetch_data(self, address, payload):
        if self.conf.server.username and self.conf.server.password:
            auth = HTTPBasicAuth(self.conf.server.username, self.conf.server.password)
        else:
            auth = None

        response = requests.post(
            address,
            json=payload,
            auth=auth,
            headers={"Content-Type": "application/json"})

        if response.status_code != 200:
            raise Exception("Failed to fetch data from GraphQL: %s" % response.text)
        return response.json()['data']
