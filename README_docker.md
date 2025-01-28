# Docker

## Run

## Build

```bash
DOCKER_BUILDKIT=1 docker build --tag 'archivepodcast' .
```

```bash
docker run \
    --rm \
    --name archivepodcast \
    --publish 5100:5100 \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast
```
