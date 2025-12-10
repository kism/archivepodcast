#!/usr/bin/env bash

set -euo pipefail

# AL
docker build -f docker/_dep_ffmpeg.Dockerfile -t archivepodcast:ffmpeg .
docker build -f docker/main_al.Dockerfile -t archivepodcast:al2023 .

# DEBIAN
docker build -f docker/_dep_ffmpeg.Dockerfile -t archivepodcast:ffmpeg .
docker build -f docker/main.Dockerfile -t archivepodcast:latest .

# PYTEST
docker build -f docker/pytest.Dockerfile -t archivepodcast:pytest .
docker run --rm archivepodcast:pytest

# SELF TEST AL
docker run --rm --env AP_SELF_TEST=true archivepodcast:al2023 sh -c "mkdir -p /app/instance && archivepodcast"
