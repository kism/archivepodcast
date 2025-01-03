# archivepodcast

![Check](https://github.com/kism/archivepodcast/actions/workflows/check.yml/badge.svg)
![CheckType](https://github.com/kism/archivepodcast/actions/workflows/check_types.yml/badge.svg)
![Test](https://github.com/kism/archivepodcast/actions/workflows/test.yml/badge.svg)
![Docker](https://github.com/kism/archivepodcast/actions/workflows/docker.yml/badge.svg)
[![codecov](https://codecov.io/gh/kism/archivepodcast/graph/badge.svg?token=FPGDA0ODT7)](https://codecov.io/gh/kism/archivepodcast)

Flask webapp that will archive a podcast from a RSS feed. It will download the episodes and re-host them.

In theory this works in windows however I haven't tested it, it ~should be able to handle windows file paths fine.

## Setup

### Install dependencies

If you want to convert WAV episodes to mp3, ensure that you have ffmpeg installed and the program will handle it automatically.

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
uv sync --no-group dev --no-group test --no-group type --no-group lint
```

## config.toml

If there is no config.toml file in the instance folder, the program will create one with the default values in archivepodcast/config.py.

The default config will not be enough to start the program as you need to define the podcasts you want to archive.

### App config 'app'

```toml
[app]
inet_path = "http://localhost:5000/"  # URL of the webapp, must match what users connect to
storage_backend = "local"             # Choices are "local" or "s3"
```

#### App webpage config 'app.web_page'

```toml
[app.web_page]
title = "Podcast Archive"             # Webpage Title
description = "My Podcast Archive"    # Webpage Description
contact = "archivepodcast@localhost"  # Contact email for the archive
```

#### App s3 config 'app.s3'

```toml
[app.s3]
cdn_domain = "https://cdn.my.cool.website/" # The public access domain of your s3 bucket
api_url = "<api url>"                       # The url of the s3 api, doesn't have to be amazon s3, cloudflare r2 is cheaper
bucket = "<bucket name>"                    # The name of the bucket
access_key_id = "<access_key_id>"           # The access key id of the s3 bucket
secret_access_key = "<secret_access_key>"   # The secret access key of the s3 bucket
```

### Podcast list

Multiple podcasts can be defined in the toml list.

```toml
[[podcast]]
url = "https://feed.articlesofinterest.club" # Feed url to archive from
new_name = "Articles of Interest [Archive]"  # override the name of the podcast. Empty string uses original
name_one_word = "aoi"                        # the http endpoint for the feed: /rss/<name_one_word>
description = ""                             # override the description of the podcast. Empty string uses original
live = true                                  # whether to actively grab new episodes, or just serve the archive
contact_email = "archivepodcast@localhost"   # override the contact email of the podcast

[[podcast]]
url = "https://feeds.megaphone.fm/replyall"
new_name = "Reply All [Archive]"
name_one_word = "replyall"
description = ""
live = true
contact_email = "archivepodcast@localhost"
```

### Logging config 'logging'

```toml
[logging]
level = "INFO" # Choices are "TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
path = ""      # Path to the log file, empty string will log to stdout
```

## Running archivepodcast webapp

This will run a webapp on <http://localhost:5000> (configurable) that will:

- Run persistently
- Host RSS feeds of the podcasts
- If `"live" : true` in config json is set it will look for and download new episodes every hour
- If you send it a SIGHUP command it will reload the configuration, be sure to check the logs to see if it was successful.

Development: `flask --app archivepodcast run --port 5000`

Production: `waitress-serve --threads=4 --listen 0.0.0.0:5000 --call archivepodcast:create_app`

An example guide on setting it up start to finish, with all features and saving episodes do disk can be found here [here](README_local.md). There are others for if you want to use s3 to host assets, or even host the whole thing on s3.

## Todo

- Container Registry
- header as a table, or divs

