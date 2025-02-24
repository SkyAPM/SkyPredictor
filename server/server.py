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

import asyncio
import logging
import os
import sys
import tempfile

import baseline
from prometheus_client import CollectorRegistry, multiprocess, start_http_server

from baseline.fetcher import GraphQLFetcher
from baseline.predict import PredictConfig
from baseline.query import Query
from baseline.result import MeterNameResultManager
from baseline.scheduler import Scheduler
from baseline.config.config import current_config


def update_log_level(name, level):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    logger.setLevel(level)


def init_logger(c: baseline.config.config.LogConfig):
    formatter = logging.Formatter(c.format)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    l = logging.getLogger()
    l.setLevel(c.level.upper())
    l.addHandler(console_handler)
    update_log_level('cmdstanpy', logging.WARN)


def setup_prometheus(port):
    if os.environ.get('PROMETHEUS_MULTIPROC_DIR') is None:
        os.environ['PROMETHEUS_MULTIPROC_DIR'] = tempfile.gettempdir()
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    start_http_server(port, registry=registry)


init_logger(current_config.logging)
logger = logging.getLogger(__name__)


def run():
    conf = PredictConfig(current_config.baseline.predict.min_days, current_config.baseline.predict.frequency,
                         current_config.baseline.predict.period)
    fetcher = GraphQLFetcher(current_config.baseline.fetch)
    result_manager = MeterNameResultManager(current_config.baseline.predict.directory)

    scheduler = Scheduler(current_config.baseline.cron, conf, fetcher, result_manager)
    scheduler.start()

    if current_config.server.monitor.enabled:
        setup_prometheus(current_config.server.monitor.port)

    loop = asyncio.get_event_loop()
    try:
        query = Query(current_config.server.grpc.port, fetcher, result_manager)
        sys.exit(loop.run_until_complete(query.serve()))
    except KeyboardInterrupt:
        logger.info("attempting graceful shutdown, press Ctrl+C again to exit…")
        quit()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if __name__ == '__main__':
    run()
