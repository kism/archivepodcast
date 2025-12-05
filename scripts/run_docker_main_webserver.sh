#!/usr/bin/env bash

set -euo pipefail

docker build -f docker/main.Dockerfile -t archivepodcast .

docker run \
    --rm \
    --name archivepodcast \
    --publish 5100:5100 \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast:latest
