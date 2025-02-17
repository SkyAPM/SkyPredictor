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

FROM python:3.13-slim as final

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the necessary files into the container
COPY . /app

EXPOSE 12800

# Set the entrypoint to run the gRPC service
ENTRYPOINT ["python3", "server.py"]
