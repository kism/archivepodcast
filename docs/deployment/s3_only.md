# S3 Storage, S3 Static Hosting

This configuration enables a fully static deployment where all application assets are served directly from S3 storage.

## Configuration Requirements

Essentially the webapp just pushes static files to s3, the webapp never has to listen on the public internet.

Same as s3 hybrid but:

- Do not setup the nginx reverse proxy
- Set the inet_path to the domain of your s3 bucket.
- Ensure that the domain / redirects to /index.html in your s3 providers settings. In cloudflare this is in website/rules/redirect rules

```{literalinclude} ../_generated/example_config_s3_only.json
:language: json
```
