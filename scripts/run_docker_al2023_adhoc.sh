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

echo_magenta "Building al2023 image"
docker build -f docker/main_al.Dockerfile -t archivepodcast:al2023 .

echo_magenta "Running al2023 image (adhoc)"
docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    --env AP_SELF_TEST=true \
    archivepodcast:al2023 \
    archivepodcast
