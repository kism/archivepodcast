# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI webapp that archives podcasts from RSS feeds: downloads episodes, rewrites the feed, and re-hosts both. Storage backend is local filesystem or S3. Three run modes share the same core: web server, adhoc CLI run, and AWS Lambda ([lambda_handler.py](archivepodcast/lambda_handler.py)).

Python 3.14 only, managed with `uv`. Frontend is plain JS in [archivepodcast/static/](archivepodcast/static/), tooling via `bun`.

## Commands

```bash
uv sync --all-extras          # setup (then: source .venv/bin/activate)
bun install                   # JS tooling

pytest                        # Python tests (coverage always on via addopts)
pytest tests/test_config.py -k test_name --no-cov   # single test, faster
bun run test                  # JS tests (vitest, tests/z_*.test.js)

ruff format . && ruff check . --fix   # Python format + lint
ty check .                    # Python type checking
bun run format && bun run check       # JS/CSS/HTML via biome
bun run spell                 # cspell

scripts/run_ci_local.sh       # everything CI runs, locally

uvicorn --factory archivepodcast:create_app --port 5100 --reload   # dev server
python -m archivepodcast      # adhoc run (one-shot archive pass)
```

Pytest runs with `--disable-socket` (only 127.0.0.1 allowed) and `--asyncio-mode=auto`; tests must not touch the network.

## Architecture

- **App factory**: `create_app()` in [archivepodcast/\_\_init\_\_.py](archivepodcast/__init__.py) — also home of `run_ap_adhoc()` for CLI mode. Config lives at `<instance_path>/config.json` (pydantic models in [config.py](archivepodcast/config.py)); it is rewritten/normalized on every startup. Instance path defaults to `./instance`, overridable via `INSTANCE_PATH` env var or `--instance-path`.
- **Module-level singletons** in [archivepodcast/instances/](archivepodcast/instances/): `health`, `event_times` (profiler), `get_app_paths()` (path helper — must be first called with `root_path`/`instance_path`, later calls take no args), `local_file_cache`/`s3_file_cache`, `get_ap_config()`, and the live `PodcastArchiver` instance. Routers and archiver code import these globals rather than passing state around.
- **Core flow**: [archiver/podcast_archiver.py](archivepodcast/archiver/podcast_archiver.py) (`PodcastArchiver`) orchestrates each archive pass → [downloader/](archivepodcast/downloader/) fetches feeds and episodes (aiohttp, ffmpeg conversion via typed-ffmpeg) → rewritten RSS and rendered webpages ([archiver/webpage_renderer.py](archivepodcast/archiver/webpage_renderer.py), Jinja templates in [archivepodcast/templates/](archivepodcast/templates/)) are written to `<instance>/web/` and optionally uploaded to S3 ([utils/s3.py](archivepodcast/utils/s3.py)). In web-server mode a background thread re-checks feeds hourly.
- **Routers** in [archivepodcast/routers/](archivepodcast/routers/): api, content, rss, static, webpages. `create_app` adds HEAD to every GET route because podcast clients probe media with HEAD requests.
- With the S3 backend, downloaded assets are uploaded then deleted locally — don't assume archived files exist on disk.

## Conventions

- Ruff runs with ALL rules selected; deviations are per-rule ignores in [pyproject.toml](pyproject.toml) with `# KG` comments explaining why. Line length 120. Get loggers via `archivepodcast.utils.logger.get_logger(__name__)`, never `logging.getLogger` directly.
- `webapp.testing: true` in config requires the instance path to be under the system tmp dir — tests rely on this guard.
- JS test files live in [tests/](tests/) with a `z_` prefix, run by vitest with happy-dom.
