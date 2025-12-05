#!/usr/bin/env bash

set -euo pipefail


docker build -f docker/_dep_ffmpeg_lambda.Dockerfile -t archivepodcast:ffmpeg-bookworm .

docker build -f docker/main.Dockerfile -t archivepodcast .

docker build -f docker/pytest.Dockerfile -t archivepodcast:pytest .

docker run --rm archivepodcast:pytest
