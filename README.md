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

- Adhoc CLI / Worker

  - Run once or on a schedule to fetch new episodes

- Rename feeds to indicate that they are an archive
- Local or S3 storage backend

## Todo

- fix readme again
- Fix font selection for frontend
- pydantic xml
- self test function to ensure ffmpeg works

Prod time to beat running adhoc, 56 seconds.
