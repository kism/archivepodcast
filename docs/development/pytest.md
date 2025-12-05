# Pytest (Python Test)

```bash
pytest
```

To get coverage report, open the `htmlcov` folder in a browser or the vscode live server.

With docker:

```bash
docker build -f tests/Dockerfile --tag archivepodcast-tests .
docker run --rm archivepodcast-tests
```
