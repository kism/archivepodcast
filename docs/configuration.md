# Config File

If there is no config.toml file in the instance folder, the program will create one with the default values in archivepodcast/config.py.

The default config will not be enough to start the program as you need to define the podcasts you want to archive.

## App Config

```toml
[app]
inet_path = "http://localhost:5100/"  # URL of the webapp, must match what users connect to
storage_backend = "local"             # Choices are "local" or "s3"
```

### App webpage config

```toml
[app.web_page]
title = "Podcast Archive"             # Webpage Title
description = "My Podcast Archive"    # Webpage Description
contact = "archivepodcast@localhost"  # Contact email for the archive
```

### App s3 config

```toml
[app.s3]
cdn_domain = "https://cdn.my.cool.website/" # The public access domain of your s3 bucket
api_url = "<api url>"                       # The url of the s3 api, doesn't have to be amazon s3, cloudflare r2 is cheaper
bucket = "<bucket name>"                    # The name of the bucket
access_key_id = "<access_key_id>"           # The access key id of the s3 bucket
secret_access_key = "<secret_access_key>"   # The secret access key of the s3 bucket
```

## Podcast list

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

## Logging config

```toml
[logging]
level = "INFO" # Choices are "TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
path = ""      # Path to the log file, empty string will log to stdout
```
