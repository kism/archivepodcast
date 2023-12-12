# Example install but use s3 as storage for assets

Same as README_local but:
* In settings.json set storagebackend to 's3'
* Fill in the s3 settings with what's appropiate for your bucket, make sure your api credential has read + write
* Ensure you s3 bucket has a domain. In settings.json set the cdndomain to that domain
