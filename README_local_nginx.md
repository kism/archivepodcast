# Hosting with nginx statically (not recommended really)

So since this webapp isn't very dynamic you can just host the webroot folder with nginx if you set it up right.

Same as README_local.md but:

* Do not use the reverse proxy settings
* Set the nginx webroot to the webroot folder in settings.json
* Set the media type for the rss feeds

```plaintext
location = /rss/<youtfeedname> {
    ### override content-type ##
    types { } default_type "application/rss+xml; charset=utf-8";

    ## override header (more like send custom header using nginx) ##
    add_header x-robots-tag "noindex, nofollow";
}
```

You might need to mess around with groups, add the nginx user to archivepodcast's group
