#!/usr/bin/env bash

set -euo pipefail

docker build -f docker/_dep_ffmpeg_al2023.Dockerfile -t archivepodcast:ffmpeg-al2023 .

docker build -f docker/main_al.Dockerfile -t archivepodcast:latest-al2023 .

docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast:latest-al2023 \
