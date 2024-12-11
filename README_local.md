
# Example install using local (disk) storage

Example install in /opt, with systemd, logging, log rotation, nginx reverse proxy

## Clone, install requirements, create service account

```bash
cd /opt
git clone https://github.com/kism/archivepodcast.git
cd archivepodcast
uv sync --no-group dev --no-group test --no-group type --no-group lint
adduser archivepodcast --shell=/bin/false --no-create-home
mkdir /var/log/archivepodcast/
chown apuser:apuser /var/log/archivepodcast
chown -R apuser:apuser /opt/archivepodcast
```

## Create Config

Run the program once manually to create the default config.toml and then fill it in. You can ignore the cdn address and s3 config items.

```bash
cd /opt/archivepodcast
sudo -u apuser .venv/bin/waitress-serve --port=5000 --call 'archivepodcast:create_app'
```

Edit: `/opt/archivepodcast/instance/config.toml` to your liking.

```toml
[app]
inet_path = "https://mycooldomain.org/"
storage_backend = "local"

[app.web_page]
title = "Podcast Archive"
description = "My Cool  Podcast Archive"
contact = "email@example.com"

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

## Systemd service

Edit: `/etc/systemd/system/archivepodcast.service`

```text
[Unit]
Description=Podcast Archiving Webapp
After=network.target

[Service]
User=apuser
WorkingDirectory=/opt/archivepodcast
ExecStart=/opt/archivepodcast/.venv/bin/waitress-serve --port=5000 --call 'archivepodcast:create_app'
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

You can use `systemctl reload archivepodcast` to reload the config, check the log to make sure it worked.

## Nginx Reverse Proxy

I wont go into detail on nginx reverse proxies, I add this as a server with my domain name. Then use certbot & certbot nginx plugin to setup https.

```text
server {
    server_name mycooldomain.org;
    location / {
        proxy_pass http://localhost:5000/;
    }
}
```
