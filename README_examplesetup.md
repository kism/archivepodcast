
# Example standalone version install
Example install in /opt, with systemd, logging, log rotation, nginx reverse proxy

## Clone, install requirements, create service account

```
cd /opt
git clone https://github.com/kism/archivepodcast.git
cd archivepodcast
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
adduser podcasto --shell=/bin/false --no-create-home
touch /var/log/archivepodcast.log
chown podcasto:podcasto /var/log/archivepodcast.log
```
## Create Config

Run the program once manually to create the default settings.json and then fill it in.
```
cd /opt/archivepodcast
/opt/archivepodcast/env/bin/python3 selfhostarchive.py --config settings.json
vim settings.json
```
## Systemd service

`vim /etc/systemd/system/archivepodcast.service`
```
[Unit]
Description=Podcast Archiving Webapp
After=network.target

[Service]
User=podcasto
WorkingDirectory=/opt/archivepodcast
ExecStart=/opt/archivepodcast/env/bin/python3 selfhostarchive.py --config settings.json --logfile /var/log/archivepodcast.log --loglevel INFO --production
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

You can use `systemctl reload archivepodcast` to reload the config, check the log to make sure it worked.

## Logrotate

`vim /etc/logrotate.d/archivepodcast`
```
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

```
server {
    server_name yourdomain.com;
    location / {
        proxy_pass http://localhost:5000/;
    }
}
```