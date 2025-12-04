# Docker

Instructions for building and running the application using Docker containers.

## Container Management

## Run

```bash
docker run \
    --rm \
    --name archivepodcast \
    --publish 5100:5100 \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    ghcr.io/kism/archivepodcast:latest
```

```bash
docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    ghcr.io/kism/archivepodcast:latest \
    python -m archivepodcast
```

## Build

```bash
DOCKER_BUILDKIT=1 docker build --tag 'archivepodcast' .
```

Then of course replace `ghcr.io/kism/archivepodcast:latest` with `archivepodcast` in the above `docker run` commands.
