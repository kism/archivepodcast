# Local Storage, Nginx static hosting

This configuration describes how to serve the application statically through nginx. Note: This method has limitations and is not recommended for production deployments.

## Configuration Requirements

So since this webapp isn't very dynamic you can just host the web root folder with nginx if you set it up right.

Same as `local.md` but:

- Do not use the reverse proxy settings
- Set the nginx web root to `<instance path>/web`
- Set the media type for the rss feeds

```text
location = /rss/<your feed name> {
    ### override content-type ##
    types { } default_type "application/rss+xml; charset=utf-8";

    ## override header (more like send custom header using nginx) ##
    add_header x-robots-tag "noindex, nofollow";
}
```

You might need to mess around with groups, add the nginx user to archivepodcast's group
