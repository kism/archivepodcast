#!/usr/bin/env bash

set -euo pipefail

docker build -f docker/pytest.Dockerfile -t archivepodcast-pytest .

docker run --rm archivepodcast-pytest
