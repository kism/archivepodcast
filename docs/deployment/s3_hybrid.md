# S3 Storage, Webapp

This configuration uses S3 for asset storage while maintaining a standard web application deployment.

## Configuration Requirements

- In config.json set storage_backend to 's3'
- Fill in the s3 config with what's appropriate for your bucket, make sure your api credential has read + write on the bucket
- Ensure you s3 bucket has a domain. In config.json set the cdn_domain to that domain

```{literalinclude} ../_generated/example_config_s3_hybrid.json
:language: json
```
