#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo_magenta() {
    echo
    echo -e "--- ${MAGENTA}$1${NC} ---"
}

# Tags match publish_docker.yml; main and lambda build FROM archivepodcast:ffmpeg, pytest FROM archivepodcast
echo_magenta "Building ffmpeg image"
docker build -f docker/_dep_ffmpeg.Dockerfile -t archivepodcast:ffmpeg .

echo_magenta "Building main image"
docker build -f docker/main.Dockerfile -t archivepodcast:latest .

echo_magenta "Building lambda image"
docker build -f docker/lambda.Dockerfile -t archivepodcast:lambda .

echo_magenta "Building pytest image"
docker build -f docker/pytest.Dockerfile -t archivepodcast:pytest .
