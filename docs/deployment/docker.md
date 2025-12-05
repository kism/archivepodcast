# Docker

Instructions for building and running the application using Docker containers.

## Container Management

## Run

Webserver:

```bash
docker run \
    --rm \
    --name archivepodcast \
    --publish 5100:5100 \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    ghcr.io/kism/archivepodcast:latest
```

Adhoc:

```bash
docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    ghcr.io/kism/archivepodcast:latest \
    archivepodcast
```
