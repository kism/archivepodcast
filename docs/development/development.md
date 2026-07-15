# Python Environment Setup

Install and configure the Python development environment:

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras
```

Run as a development server

```bash
uvicorn --factory archivepodcast:create_app --port 5100 --reload
```

The Swagger UI is available at `/docs`. To enable `/api/reload`, set `"debug": true` in the `webapp` section of config.json. Note that config reload via SIGHUP only works in single-process mode; `--reload` and `--workers` supervisors intercept SIGHUP.

Run adhoc

```bash
python -m archivepodcast
```

# Out of scope

- uvloop, no performance upgrade found
- authentication, nope
