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
import datetime
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import urlparse


class MetricValueConfig:
    def __init__(self, min_value: int, max_value: int):
        self.min = min_value
        self.max = max_value


class MetricConfig:
    def __init__(self, single_conf: Optional[MetricValueConfig] = None,
                 multi_conf: Optional[list[tuple[list[tuple[str, str], MetricValueConfig]]]] = None):
        self.single_conf = single_conf
        self.multi_conf = multi_conf


supported_metrics = {
    'service_cpm': MetricConfig(single_conf=MetricValueConfig(0, 100)),
    'service_percentile': MetricConfig(multi_conf=[
        ([('p', '50')], MetricValueConfig(0, 100)),
        ([('p', '90')], MetricValueConfig(0, 100)),
        ([('p', '99')], MetricValueConfig(0, 100)),
    ]),
}


class MockOAPRequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/status/config/ttl":
            response = {"metrics": {"day": 7}}
        else:
            response = {"error": "Not Found"}
            self._set_headers(404)
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        self._set_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length else b"{}"

        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON format"}).encode("utf-8"))
            return

        if path == "/graphql":
            return self.handle_graphql(data)
        else:
            response = {"error": "Not Found: " + path}
            self._set_headers(404)
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

    def handle_graphql(self, query_data):
        query = query_data["query"]

        if 'listServices' in query:
            self._set_headers()
            self.wfile.write(json.dumps({'data': {'services': [{'label': 'test-service', 'normal': 'true'}]}}).encode("utf-8"))
            return

        data = None
        for metric_name in supported_metrics:
            if metric_name in query:
                conf = supported_metrics[metric_name]
                time_buckets = generate_metrics_time_buckets(query_data['variables'])
                data = generate_metrics_values(conf, time_buckets)

        self._set_headers()
        if data is not None:
            self.wfile.write(json.dumps({'data': {'result': data}}).encode("utf-8"))
        else:
            self.wfile.write(json.dumps({'data': 'not found'}).encode("utf-8"))


def generate_metrics_values(conf: MetricConfig, times: [int]) -> dict:
    if conf.single_conf is not None:
        return {
            'type': 'TIME_SERIES_VALUES',
            'results': [{
                'metric': {'labels': []},
                'values': [{'id': t, 'value': random.randint(conf.single_conf.min, conf.single_conf.max)} for t in
                           times]
            }]
        }
    elif conf.multi_conf is not None:
        results = []
        label_conf = conf.multi_conf
        for labels, meter_conf in label_conf:
            results.append({
                'metric': {'labels': [{'key': k, 'value': v} for k, v in labels]},
                'values': [{'id': t, 'value': random.randint(meter_conf.min, meter_conf.max)} for t in times]
            })
        return {
            'type': 'TIME_SERIES_VALUES',
            'results': results
        }
    return None


def generate_metrics_time_buckets(parameter: dict) -> [int]:
    step = parameter['duration']['step'].lower()
    start = parameter['duration']['start']
    end = parameter['duration']['end']

    if step == 'hour':
        start_time = datetime.datetime.strptime(start, '%Y-%m-%d %H')
        end_time = datetime.datetime.strptime(end, '%Y-%m-%d %H')
        times = []
        while start_time <= end_time:
            times.append(int(start_time.timestamp() * 1000))
            start_time += datetime.timedelta(hours=1)
        return times
    elif step == 'minute':
        start_time = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M')
        end_time = datetime.datetime.strptime(end, '%Y-%m-%d %H:%M')
        times = []
        while start_time <= end_time:
            times.append(start_time.timestamp() * 1000)
            start_time += datetime.timedelta(minutes=1)
        return times
    return None


def run(server_class=HTTPServer, handler_class=MockOAPRequestHandler, port=12800):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting HTTP server on port {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
