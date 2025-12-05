#!/usr/bin/env bash

set -euo pipefail

docker build -f docker/main.Dockerfile -t archivepodcast .

docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast:latest \
    archivepodcast
