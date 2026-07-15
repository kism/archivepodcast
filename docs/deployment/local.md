# Local Storage, Webapp

This guide details the process of deploying the application using local storage with systemd service management and nginx reverse proxy.

## Initial Setup

Example install in /opt, with systemd, logging, log rotation, nginx reverse proxy

### Clone, install requirements, create service account

```bash
cd /opt
git clone https://github.com/kism/archivepodcast.git
cd archivepodcast
uv sync --no-default-groups
adduser archivepodcast --shell=/bin/false --no-create-home
mkdir /var/log/archivepodcast/
chown apuser:apuser /var/log/archivepodcast
chown -R apuser:apuser /opt/archivepodcast
```

## Configuration

Run the program once manually to create the default config.json and then fill it in. You can ignore the cdn address and s3 config items.

```bash
cd /opt/archivepodcast
sudo -u apuser .venv/bin/uvicorn --factory 'archivepodcast:create_app' --port 5100
```

Edit: `/opt/archivepodcast/instance/config.json` to your liking.

```{literalinclude} ../_generated/example_config_local.json
:language: json
```

## Service Configuration

Edit: `/etc/systemd/system/archivepodcast.service`

```text
[Unit]
Description=Podcast Archiving Webapp
After=network.target

[Service]
User=apuser
WorkingDirectory=/opt/archivepodcast
ExecStart=/opt/archivepodcast/.venv/bin/uvicorn --factory 'archivepodcast:create_app' --port 5100
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

You can use `systemctl reload archivepodcast` to reload the config, check the log to make sure it worked.

## Web Server Configuration

I wont go into detail on nginx reverse proxies, I add this as a server with my domain name. Then use certbot & certbot nginx plugin to setup https.

```text
server {
    server_name mycooldomain.org;
    location / {
        proxy_pass http://localhost:5100/;
    }
}
```
