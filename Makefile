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

SHA := $(shell git rev-parse HEAD)
VERSION ?= $(SHA)
HUB ?= sky-predictor
CONTAINER_PLATFORMS ?= --platform linux/amd64,linux/arm64

# determine host platform
ifeq ($(OS),Windows_NT)
    OS := Windows
else ifeq ($(shell uname -s),Darwin)
    OS := Darwin
else
    OS := $(shell sh -c 'uname 2>/dev/null || echo Unknown')
endif

.PHONY: all
gen:
	poetry run python -m baseline.proto.generate

poetry:
ifeq ($(OS),Windows)
	-powershell (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
	poetry self update
else
	-curl -sSL https://install.python-poetry.org | python3 -
	export PATH="$HOME/.local/bin:$PATH"
	poetry self update || $(MAKE) poetry-fallback
endif

.PHONY: install
install:
	python3 -m pip install .[all]

docker: PLATFORMS =
docker: LOAD_OR_PUSH = --load

docker.push: PLATFORMS = ${CONTAINER_PLATFORMS}
docker.push: LOAD_OR_PUSH = --push

docker docker.push:
	$(DOCKER_RULE)

define DOCKER_RULE
	docker buildx build ${PLATFORMS} ${LOAD_OR_PUSH} \
		-t $(HUB)/sky-predictor:$(VERSION) \
		-t $(HUB)/sky-predictor:latest --no-cache . -f Dockerfile
endef

