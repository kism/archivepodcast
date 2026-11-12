# Docker

## Main Container

```bash
docker build -f docker/main.Dockerfile -t archivepodcast .
```

Webserver:

```bash
docker run \
    --rm \
    --name archivepodcast \
    --publish 5100:5100 \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast:latest
```

Adhoc:

```bash
docker run \
    --rm \
    --name archivepodcast \
    --mount type=bind,source="$(pwd)"/instance,target=/app/instance \
    archivepodcast:latest \
    archivepodcast
```

## Pytest Container

```bash
docker build -f docker/pytest.Dockerfile -t archivepodcast-pytest .
```

```bash
docker run --rm archivepodcast-pytest:latest
```

Check the diff to main:

```bash
code --diff docker/main.Dockerfile docker/pytest.Dockerfile
```

## Lambda Container

```bash
docker build -f docker/lambda.Dockerfile -t archivepodcast-lambda .
```

```bash
docker run -p 9000:8080 \
  -v $(pwd)/instance:/opt/instance:ro \
  archivepodcast-lambda
```

In another terminal, invoke the function:

```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
```
