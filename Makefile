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
	poetry run python -m proto.generate

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

