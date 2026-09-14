#!/usr/bin/env bash

set -euo pipefail

MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo_magenta() {
    echo
    echo -e "--- ${MAGENTA}$1${NC} ---"
}

echo_magenta "Building ffmpeg image"
docker build -f docker/_dep_ffmpeg.Dockerfile -t archivepodcast:ffmpeg .
docker build -f docker/main_al.Dockerfile -t archivepodcast:al2023 .

echo_magenta "Building main image"
docker build -f docker/_dep_ffmpeg.Dockerfile -t archivepodcast:ffmpeg .
docker build -f docker/main.Dockerfile -t archivepodcast:latest .

echo_magenta "Building pytest image"
docker build -f docker/pytest.Dockerfile -t archivepodcast:pytest .

echo_magenta "Running pytest image"
docker run --rm archivepodcast:pytest

echo_magenta "Running self test"
docker run --rm --env AP_SELF_TEST=true archivepodcast:al2023 sh -c "mkdir -p /tmp/instance && archivepodcast --instance-path /tmp/instance"
