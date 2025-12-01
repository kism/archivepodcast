# Archive Podcast

[![Check](https://github.com/kism/archivepodcast/actions/workflows/check.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/check.yml)
[![CheckType](https://github.com/kism/archivepodcast/actions/workflows/check_types.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/check_types.yml)
[![Test](https://github.com/kism/archivepodcast/actions/workflows/test.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/kism/archivepodcast/graph/badge.svg?token=FPGDA0ODT7)](https://codecov.io/gh/kism/archivepodcast)
[![Docker](https://github.com/kism/archivepodcast/actions/workflows/docker.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/docker.yml)
[![SpellCheck](https://github.com/kism/archivepodcast/actions/workflows/spell_check.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/spell_check.yml)

Flask webapp that will archive a podcast from a RSS feed. It will download the episodes and re-host them.

Features:

- Webapp
  - List of feeds hosted
  - File listing for unlisted episodes
  - Web player
  - Health check page
- Looks for new episodes to fetch every hour
- Rename feeds to indicate that they are an archive
- Local or S3 storage backend

In theory this works in windows however I haven't tested it, it ~should be able to handle windows file paths fine.

Docs are at <https://archivepodcast.readthedocs.io/en/latest/>

## Setup

### Install dependencies

You will need to install ffmpeg for your platform. Should be on your package manager or download the binary to /usr/local/bin.

You will need to install git-lfs for your platform to fetch the .woff font files.

If you cloned the repo without git-lfs installed, run the following commands to fetch the files:

```bash
git lfs install
git lfs fetch --all
git lfs pull
```

### Pre Commit Hooks

To set up pre-commit hooks run:

```bash
uv tool add pre-commit --upgrade
pre-commit install
```

### Setup Python Environment

#### Development

```bash
uv venv
source .venv/bin/activate
uv sync
```

#### Production

```bash
uv venv
source .venv/bin/activate
uv sync --no-default-groups
```

## Running archivepodcast webapp

This will run a webapp on <http://localhost:5100> (configurable) that will:

- Run persistently
- Host RSS feeds of the podcasts
- If `"live" : true` in config toml is set it will look for and download new episodes every hour
- If you send it a SIGHUP command it will reload the configuration, be sure to check the logs to see if it was successful.

Development: `flask --app archivepodcast run --port 5100`

Production: `waitress-serve --threads=4 --listen 0.0.0.0:5100 --call archivepodcast:create_app`

An example guide on setting it up start to finish, with all features and saving episodes do disk can be found in the docs. There are others for if you want to use s3 to host assets, or even host the whole thing on s3.

## Todo

- Patch asyncio.sleep for pytest
- Container Registry
- header as a table, or divs
- Fix font selection for frontend, done?
- Cloudflare worker cron (CF still in beta)
  - Terraform example
- pydantic xml

Prod time to beat running adhoc, 56 seconds.
