# Example install but host everything on s3

Essentially the webapp just pushes static files to s3, the webapp never has to listen on the public internet.

Same as s3 hybrid but:
* Do not setup the nginx reverse proxy
* Set the inetpath to the domain of your s3 bucket.
* Ensure that the domain / redirects to /index.html in your s3 providers settings. In cloudflare this is in website/rules/redirect rules

