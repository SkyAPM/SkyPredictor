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
from concurrent import futures

import pandas as pd

import grpc

from baseline.fetcher import Fetcher
from baseline.result import ResultManager
from baseline.predict import PredictMeterResult, PredictTimestampWithSingleValue, PredictLabeledWithLabeledValue, \
    LabelKeyValue
from proto.generated.baseline_pb2 import AlarmBaselineRequest, AlarmBaselineServiceMetric, AlarmBaselineResponse, \
    AlarmBaselineMetricPrediction, AlarmBaselinePredicatedValue, TimeBucketStep, AlarmBaselineSingleValue, \
    AlarmBaselineValue, KeyStringValuePair, AlarmBaselineLabeledValue, AlarmBaselineMetricsNames
from proto.generated.baseline_pb2_grpc import AlarmBaselineServiceServicer
from proto.generated.baseline_pb2_grpc import add_AlarmBaselineServiceServicer_to_server

logger = logging.getLogger(__name__)


class Query:

    def __init__(self, port: int, fetcher: Fetcher, result_manager: ResultManager):
        self.grpc_port = port
        self.fetcher = fetcher
        self.result_manager = result_manager

    async def serve(self):
        server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

        server.add_insecure_port('[::]:%s' % self.grpc_port)
        add_AlarmBaselineServiceServicer_to_server(BaselineQueryServer(self.fetcher, self.result_manager), server)

        await server.start()

        logger.info('gRPC Server started at :%s' % self.grpc_port)

        await server.wait_for_termination()


class BaselineQueryServer(AlarmBaselineServiceServicer):

    def __init__(self, fetcher: Fetcher, result_manager: ResultManager):
        self.result_manager = result_manager
        self.support_metrics_names = fetcher.metric_names()

    async def querySupportedMetricsNames(self, request, context):
        logger.info('receive query supported metrics names query')
        return AlarmBaselineMetricsNames(metricNames=self.support_metrics_names)

    async def queryPredictedMetrics(self, request: AlarmBaselineRequest, context):
        logger.info(
            f"receive query predict metrics query, total service with metrics count: {len(request.serviceMetricNames)}")
        results: dict[str, dict[str, list[PredictMeterResult]]] = {}
        for serviceWithMetrics in request.serviceMetricNames:
            predict_metrics = self.result_manager.query(serviceWithMetrics.serviceName,
                                                        list(serviceWithMetrics.metricNames),
                                                        request.startTimeBucket, request.endTimeBucket, request.step)
            for metric_name, result in predict_metrics.items():
                if serviceWithMetrics.serviceName not in results:
                    results[serviceWithMetrics.serviceName] = {}
                metrics_vals = results[serviceWithMetrics.serviceName]
                if metric_name not in metrics_vals:
                    metrics_vals[metric_name] = []
                metric_val = metrics_vals[metric_name]
                for r in result:
                    metric_val.append(r)

        serviceMetrics: list[AlarmBaselineServiceMetric] = []
        for service, metricsWithPredictValues in results.items():
            predictions = []
            for metric_name, result in metricsWithPredictValues.items():
                predictions.append(convert_response_metrics(service, metric_name, result, request.step))
            serviceMetrics.append(AlarmBaselineServiceMetric(
                serviceName=service,
                predictions=predictions
            ))

        return AlarmBaselineResponse(serviceMetrics=serviceMetrics)


def convert_response_metrics(service: str, metric_name: str, results: list[PredictMeterResult],
                             step: TimeBucketStep) -> AlarmBaselineMetricPrediction:
    for result in results:
        if result.single is not None:
            return AlarmBaselineMetricPrediction(name=metric_name,
                                                 values=convert_response_single_value(result.single, step))
        elif result.labeled is not None:
            return AlarmBaselineMetricPrediction(name=metric_name,
                                                 values=convert_response_multiple_value(result.labeled, step))


def convert_response_single_value(values: list[PredictTimestampWithSingleValue], step: TimeBucketStep) -> list[
    AlarmBaselinePredicatedValue]:
    result = []
    for value in values:
        result.append(AlarmBaselinePredicatedValue(
            timeBucket=convert_response_time_bucket(value.timestamp, step),
            singleValue=AlarmBaselineSingleValue(
                value=AlarmBaselineValue(
                    value=int(value.value.value),
                    upperValue=int(value.value.upper_value),
                    lowerValue=int(value.value.lower_value)
                )
            )
        ))
    return result


def convert_response_multiple_value(values: list[PredictLabeledWithLabeledValue], step: TimeBucketStep) -> list[
    AlarmBaselinePredicatedValue]:
    time_values: dict[int, list[AlarmBaselineLabeledValue.LabelWithValue]] = {}
    for val in values:
        labels = convert_response_labels(val.label)
        for time_with_value in val.time_with_values:
            time_bucket = convert_response_time_bucket(time_with_value.timestamp, step)
            if time_bucket not in time_values:
                time_values[time_bucket] = []
            time_values[time_bucket].append(AlarmBaselineLabeledValue.LabelWithValue(
                labels=labels,
                value=AlarmBaselineValue(
                    value=int(time_with_value.value.value),
                    upperValue=int(time_with_value.value.upper_value),
                    lowerValue=int(time_with_value.value.lower_value)
                )
            ))

    result = []
    for time_bucket, vals in time_values.items():
        result.append(AlarmBaselinePredicatedValue(
            timeBucket=time_bucket,
            labeledValue=AlarmBaselineLabeledValue(values=vals)
        ))
    return result


def convert_response_time_bucket(ts: pd.Timestamp, step: TimeBucketStep) -> int:
    if step == TimeBucketStep.HOUR:
        return int(ts.strftime('%Y%m%d%H'))
    return 0


def convert_response_labels(labels: frozenset[LabelKeyValue]) -> list[KeyStringValuePair]:
    result = []
    for l in labels:
        result.append(KeyStringValuePair(
            key=l.key,
            value=l.value
        ))
    return result
