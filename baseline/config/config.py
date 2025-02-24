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

import os
import re
from typing import List, Optional

import yaml
from pydantic import BaseModel, model_validator

current_dir = os.path.dirname(os.path.realpath(__file__))

env_regular_regex = re.compile(r'\${(?P<ENV>[_A-Z0-9]+):(?P<DEF>.*)}')


class LogConfig(BaseModel):
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class MonitorConfig(BaseModel):
    enabled: bool = False
    port: int = 8000


class GRPCConfig(BaseModel):
    port: int = 18080


class ServerConfig(BaseModel):
    grpc: GRPCConfig
    monitor: MonitorConfig


class BaselineFetchMetricsTagMappingConfig(BaseModel):
    key: str
    value: str


class BaselineFetchValuePreProcessConfig(BaseModel):
    hour_to_minute: bool = False


class BaselineFetchMetricsConfig(BaseModel):
    name: str
    enabled: bool
    pre_process: Optional[BaselineFetchValuePreProcessConfig] = None


class BaselineFetchGraphqlServerConfig(BaseModel):
    address: str
    username: Optional[str]
    password: Optional[str]
    down_sampling: str = "HOUR"
    layers: List[str]

    @model_validator(mode="before")
    @classmethod
    def convert_layers(cls, values):
        if isinstance(values.get("layers"), str):
            values["layers"] = [layer.strip() for layer in values["layers"].split(",")]
        return values


class BaselineFetchConfig(BaseModel):
    server: BaselineFetchGraphqlServerConfig
    metrics: List[str]

    @model_validator(mode="before")
    @classmethod
    def convert_layers(cls, values):
        if isinstance(values.get("metrics"), str):
            values["metrics"] = [metrics.strip() for metrics in values["metrics"].split(",")]
        return values


class BaselinePredictConfig(BaseModel):
    directory: str = "/tmp"
    min_days: int = 3
    frequency: str = 'h'
    period: int = 24


class BaselineConfig(BaseModel):
    cron: str = "0 0 * * *"
    fetch: BaselineFetchConfig
    predict: BaselinePredictConfig


def parse_env_variables(value):
    if isinstance(value, str):
        match = env_regular_regex.match(value)
        if match:
            env_var, default_value = match.groups()
            return os.getenv(env_var, default_value)
    return value


def parse_nested_values(values):
    if isinstance(values, dict):
        for key, val in values.items():
            if isinstance(val, str):
                values[key] = parse_env_variables(val)
            elif isinstance(val, dict):
                values[key] = parse_nested_values(val)
            elif isinstance(val, list):
                values[key] = [parse_nested_values(item) if isinstance(item, dict) else parse_env_variables(item) for
                               item in val]
    return values


class Config(BaseModel):
    logging: LogConfig
    server: ServerConfig
    baseline: BaselineConfig

    @model_validator(mode="before")
    def replace_env_variables(cls, values):
        return parse_nested_values(values)


with open(os.path.join(current_dir, "config.yaml"), "r") as f:
    yamlLoadedConfig = yaml.safe_load(f)

current_config = Config(**yamlLoadedConfig)
