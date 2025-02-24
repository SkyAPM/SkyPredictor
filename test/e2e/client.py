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
"""
Run this file to get a web demo of the URI Drain algorithm.
"""
import datetime
import sys

import google
import grpc
import yaml

from baseline.proto.generated.baseline_pb2 import AlarmBaselineRequest, AlarmBaselineServiceMetricName
from baseline.proto.generated.baseline_pb2_grpc import AlarmBaselineServiceStub

from google.protobuf.json_format import MessageToDict

mode = sys.argv[1]

channel = grpc.insecure_channel('localhost:18080')
stub = AlarmBaselineServiceStub(channel)


def metric_names():
    names = stub.querySupportedMetricsNames(google.protobuf.empty_pb2.Empty())
    print(grpc_response_to_yaml(names))


def predict_values():
    service_name = sys.argv[2]
    metrics_name = sys.argv[3]
    start_time = datetime.datetime.now() + datetime.timedelta(hours=1)
    end_time = datetime.datetime.now() + datetime.timedelta(hours=5)

    metrics = stub.queryPredictedMetrics(AlarmBaselineRequest(
        serviceMetricNames=[
            AlarmBaselineServiceMetricName(serviceName=service_name, metricNames=[metrics_name])
        ],
        startTimeBucket=int(start_time.strftime('%Y%m%d%H')),
        endTimeBucket=int(end_time.strftime('%Y%m%d%H')),
        step='HOUR'
    ))
    print(grpc_response_to_yaml(metrics))


def grpc_response_to_yaml(response):
    response_dict = MessageToDict(response, preserving_proto_field_name=True)
    yaml_output = yaml.dump(response_dict, allow_unicode=True, default_flow_style=False)
    return yaml_output


if __name__ == '__main__':
    if mode == 'metrics':
        metric_names()
    elif mode == 'predict':
        predict_values()
