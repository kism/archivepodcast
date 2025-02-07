# Docker

Instructions for building and running the application using Docker containers.

## Container Management

## Build

```bash
DOCKER_BUILDKIT=1 docker build --tag 'archivepodcast' .
```

## Run

```bash
docker run \
    --rm \
    --name archivepodcast \
    --publish 5100:5100 \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast
```
