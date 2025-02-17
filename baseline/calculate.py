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
import traceback
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

from baseline.fetcher import Fetcher
from baseline.predict import PredictService, PredictConfig
from baseline.result import ResultManager

log = logging.getLogger(__name__)


class Calculator:

    def __init__(self, conf: PredictConfig, fetcher: Fetcher, saver: ResultManager):
        self.conf = conf
        self.fetcher = fetcher
        self.saver = saver

    def start(self):
        futures = {}
        with ProcessPoolExecutor() as executor:
            metric_names = self.fetcher.metric_names()
            if not metric_names:
                log.error("No metric names found")
                return
            try:
                self.fetcher.ready_fetch()
            except Exception as e:
                log.error(f"Ready to fetch data failure, skip calculate predict: {e}, stacktrace: {"".join(traceback.format_exception(type(e), e, e.__traceback__))}")
                return
            for inx in range(len(metric_names)):
                meter = metric_names[inx]
                log.info("Calculating baseline for %s" % meter)

                future = executor.submit(PredictService(self.fetcher, meter, self.conf).predict)
                futures[future] = meter

            while futures:
                done, remaining_futures = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        result = future.result()
                        meter = futures[future]
                        self.saver.save(meter, result)
                    except Exception as e:
                        log.error(f"Calculate or saving metrics failure: {e}, stacktrace: {"".join(traceback.format_exception(type(e), e, e.__traceback__))}")
                futures = {future: futures[future] for future in remaining_futures}