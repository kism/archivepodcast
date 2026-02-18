# Python Environment Setup

Install and configure the Python development environment:

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras
```

Run as a development server

```bash
flask --app archivepodcast run --port 5100
```

Run adhoc

```bash
python -m archivepodcast
```

# Out of scope

- uvloop, no performance upgrade found
- authentication, nope
