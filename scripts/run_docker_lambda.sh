#!/usr/bin/env bash

docker build -f docker/lambda.Dockerfile -t archivepodcast-lambda .

# Enable the self-test mode to verify dependencies during build
docker run -p 9000:8080 \
  -v $(pwd)/instance:/opt/instance:ro \
  --env AP_SELF_TEST=1 \
  archivepodcast-lambda
