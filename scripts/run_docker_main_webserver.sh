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

echo_magenta "Building main image"
docker build -f docker/main.Dockerfile -t archivepodcast:latest .

echo_magenta "Running main image (webserver)"
docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    --publish 5100:5100 \
    archivepodcast:latest
