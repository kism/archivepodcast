# Example install but use s3 as storage for assets

Same as README_local but:

* In config.toml set storage_backend to 's3'
* Fill in the s3 settings with what's appropriate for your bucket, make sure your api credential has read + write on the bucket
* Ensure you s3 bucket has a domain. In config.toml set the cdn_domain to that domain

```toml
[app]
inet_path = "https://mycooldomain.org/"
storage_backend = "local"

[app.web_page]
title = "Podcast Archive"
description = "My Cool  Podcast Archive"
podcast_guide = "https://medium.com/@joshmuccio/how-to-manually-add-a-rss-feed-to-your-podcast-app-on-desktop-ios-android-478d197a3770" podcast app
contact = "email@example.com"

[app.s3]
cdn_domain = "https://cdn.mycooldomain.org/"
api_url = "<api url>"
bucket = "<bucket name>"
access_key_id = "<access_key_id>"
secret_access_key = "<secret_access_key>"

[[podcast]]
url = "https://feeds.megaphone.fm/replyall"
new_name = "Reply All [Archive]"
name_one_word = "replyall"
description = ""
live = true
contact_email = "archivepodcast@localhost"

[logging]
level = "INFO"
path = ""
```
