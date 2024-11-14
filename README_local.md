
# Example install using local (disk) storage

Example install in /opt, with systemd, logging, log rotation, nginx reverse proxy

## Clone, install requirements, create service account

```bash
cd /opt
git clone https://github.com/kism/archivepodcast.git
cd archivepodcast
pipenv install --dev
adduser archivepodcast --shell=/bin/false --no-create-home
touch /var/log/archivepodcast.log
chown archivepodcast:archivepodcast /var/log/archivepodcast.log
chown -R archivepodcast:archivepodcast /opt/archivepodcast
```

## Create Config

Run the program once manually to create the default settings.json and then fill it in. You can ignore the cdn address and s3 settings.

```bash
cd /opt/archivepodcast
/opt/archivepodcast/env/bin/python3 archivepodcast.py --config settings.json
vim settings.json
```

## Systemd service

```bash
vim /etc/systemd/system/archivepodcast.service
```

```text
[Unit]
Description=Podcast Archiving Webapp
After=network.target

[Service]
User=archivepodcast
WorkingDirectory=/opt/archivepodcast
ExecStart=/usr/sbin/pipenv run python3 archivepodcast.py --config settings.json --logfile /var/log/archivepodcast.log --loglevel INFO --production
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

You can use `systemctl reload archivepodcast` to reload the config, check the log to make sure it worked.

## Logrotate

```bash
vim /etc/logrotate.d/archivepodcast
```

```text
/var/log/archivepodcast.log
{
    rotate 6
    daily
    missingok
    dateext
    copytruncate
    notifempty
    compress
}
```

## Nginx Reverse Proxy

I wont go into detail on nginx reverse proxys, I add this as a server with my domain name. Then use certbot & certbot nginx plugin to setup https.

```text
server {
    server_name yourdomain.com;
    location / {
        proxy_pass http://localhost:5000/;
    }
}
```
