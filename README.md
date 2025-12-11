# Archive Podcast

[![Check](https://github.com/kism/archivepodcast/actions/workflows/check.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/check.yml)
[![CheckType](https://github.com/kism/archivepodcast/actions/workflows/check_types.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/check_types.yml)
[![Test](https://github.com/kism/archivepodcast/actions/workflows/test.yml/badge.svg)](https://github.com/kism/archivepodcast/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/kism/archivepodcast/graph/badge.svg?token=FPGDA0ODT7)](https://codecov.io/gh/kism/archivepodcast)
![PyPI - Version](https://img.shields.io/pypi/v/archivepodcast)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fkism%2Farchivepodcast%2Frefs%2Fheads%2Fmain%2Fpyproject.toml)

Flask webapp that will archive a podcast from a RSS feed. It will download the episodes and re-host them.

Features:

- Webapp

  - List of feeds hosted
  - File listing for unlisted episodes
  - Web player
  - Health check page
  - Looks for new episodes to fetch every hour

- Adhoc CLI / Worker

  - Run once or on a schedule to fetch new episodes

- Rename feeds to indicate that they are an archive
- Local or S3 storage backend

## Todo

- logic for not uploading rss if no diff, remove 'previous feed' logic
- bump lxml, naa still cooked
- serverless
  - config from s3
- fix readme again
- pydantic xml
- self test function to ensure ffmpeg works

Prod time to beat running adhoc, 56 seconds.
