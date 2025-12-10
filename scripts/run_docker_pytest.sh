#!/usr/bin/env bash

set -euo pipefail

# AL
docker build -f docker/_dep_ffmpeg_al2023.Dockerfile -t archivepodcast:ffmpeg-al2023 .
docker build -f docker/main_al.Dockerfile -t archivepodcast:al2023 .

# DEBIAN
docker build -f docker/_dep_ffmpeg_bookworm.Dockerfile -t archivepodcast:ffmpeg-bookworm .
docker build -f docker/main.Dockerfile -t archivepodcast:latest .

# PYTEST
docker build -f docker/pytest.Dockerfile -t archivepodcast:pytest .

# SELF TEST AL
docker run --rm archivepodcast:pytest
DOCKER_INSTANCE_DIR=/tmp/docker_instance
rm -rf "$DOCKER_INSTANCE_DIR"
mkdir -p "$DOCKER_INSTANCE_DIR"
docker run --rm --env AP_SELF_TEST=true --mount type=bind,source="$DOCKER_INSTANCE_DIR",target=/app/instance archivepodcast:al2023 archivepodcast
