# Run ad-hoc

When you run the flask app, it will stay running and check for new episodes every hour, alternately you can run the app as a once-off.

- Fetches new episodes
- Generates webpages to instance folder
- Takes arguments

## Run

By default, it will look for config.json in the usual paths, and the instance path is the current working directory / instance.

```bash
.venv/bin/python -m archivepodcast
```

Alternatively you can specify either of these as arguments.

```bash
.venv/bin/python -m archivepodcast --instance-path path/to/instance
```
