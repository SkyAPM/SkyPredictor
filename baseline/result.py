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

import json
import logging
import os
from abc import abstractmethod, ABC
from collections import defaultdict

import pandas as pd

from baseline.predict import PredictMeterResult
from proto.generated.baseline_pb2 import TimeBucketStep

log = logging.getLogger(__name__)


class ResultManager(ABC):

    @abstractmethod
    def save(self, meter_name: str, results: list[PredictMeterResult]):
        pass

    @abstractmethod
    def query(self, service_name: str, metrics_names: list[str], start_bucket: int, end_bucket: int,
              step: TimeBucketStep) -> dict[str, list[PredictMeterResult]]:
        pass


class MeterNameResultManager(ResultManager):

    def __init__(self, dir: str):
        self.dir = dir

    def save(self, meter_name: str, results: list[PredictMeterResult]):
        grouped_results = defaultdict(dict)
        for result in results:
            grouped_results[result.service_name] = result
        file_name = f"{self.dir}/{meter_name}.json"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(grouped_results, f, ensure_ascii=False, separators=(',', ':'), cls=ResultEncoder)

    def query(self, service_name: str, metrics_names: list[str], start_bucket: int, end_bucket: int,
              step: TimeBucketStep) -> dict[str, list[PredictMeterResult]]:
        results: dict[str, list[PredictMeterResult]] = {}
        startTs, endTs = time_bucket_to_timestamp(start_bucket, step), time_bucket_to_timestamp(end_bucket, step)
        for meter_name in metrics_names:
            file_name = f"{self.dir}/{meter_name}.json"
            if os.path.exists(file_name):
                with open(file_name, 'r', encoding='utf-8') as f:
                    try:
                        file_content = f.read()
                        data = json.loads(file_content, object_hook=json_load_object_hook)
                        if service_name in data:
                            service_results = PredictMeterResult.from_dict(data[service_name])
                            service_results.filter_time(startTs, endTs)
                            if meter_name not in results:
                                results[meter_name] = []
                            results[meter_name].append(service_results)
                    except json.JSONDecodeError as e:
                        log.error(f"parsing baseline result file failure, filepath: {file_name}, error: {e}")
            else:
                log.info(f"cannot found the baseline result file: filepath: {file_name}")
        return results


def time_bucket_to_timestamp(bucket: int, step: TimeBucketStep) -> pd.Timestamp:
    if step == TimeBucketStep.HOUR:
        return pd.to_datetime(f"{bucket}", format="%Y%m%d%H")
    log.warning(f"detect the time bucket query is not hour, baseline is not support for now, current: {step}")
    return pd.Timestamp(0)


class ResultEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, frozenset):
            return list(obj)
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


def json_load_object_hook(dct):
    if 'timestamp' in dct:
        dct['timestamp'] = pd.to_datetime(dct['timestamp'])
    return dct
