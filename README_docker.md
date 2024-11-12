# Docker

## Run

## Build

```bash
DOCKER_BUILDKIT=1 docker build --tag 'archivepodcast' .
```

```bash
docker run \
    --name archivepodcast \
    --publish 5000:5000 \
    --mount type=bind,source="$(pwd)"/instance,target=/instance \
    archivepodcast
```
