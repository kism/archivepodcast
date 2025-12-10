#!/usr/bin/env bash

set -euo pipefail

docker build -f docker/_dep_ffmpeg.Dockerfile -t archivepodcast:ffmpeg .
docker build -f docker/main.Dockerfile -t archivepodcast:latest .

docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    --publish 5100:5100 \
    archivepodcast:latest
