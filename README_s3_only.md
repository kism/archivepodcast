# Example install but host everything on s3

Essentially the webapp just pushes static files to s3, the webapp never has to listen on the public internet.

Same as s3 hybrid but:

* Do not setup the nginx reverse proxy
* Set the inet_path to the domain of your s3 bucket.
* Ensure that the domain / redirects to /index.html in your s3 providers settings. In cloudflare this is in website/rules/redirect rules

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
cdn_domain = "https://mycooldomain.org/"
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
