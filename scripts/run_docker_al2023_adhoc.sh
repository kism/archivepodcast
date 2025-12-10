#!/usr/bin/env bash

set -euo pipefail

docker build -f docker/_dep_ffmpeg.Dockerfile -t archivepodcast:ffmpeg .
docker build -f docker/main_al.Dockerfile -t archivepodcast:al2023 .

docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    --env AP_SELF_TEST=true \
    archivepodcast:al2023 \
    archivepodcast
