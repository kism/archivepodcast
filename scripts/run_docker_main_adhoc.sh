#!/usr/bin/env bash

set -euo pipefail

docker build -f docker/_dep_ffmpeg_lambda.Dockerfile -t archivepodcast:ffmpeg-bookworm .

docker build -f docker/main.Dockerfile -t archivepodcast .

docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast:latest \
    archivepodcast
