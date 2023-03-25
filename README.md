# archivepodcast.py THIS IS BROKEN RN AND I BORKED THE BRANCHES

This Python script mirrors a podcast, it is indended to be used alongside nginx to create a mirror of a podcast.

## How to do

`git clone https://github.com/kism/archivepodcast.git`

`cd archivepodcast`

`python3 -m venv env`

`source env/bin/activate`

`pip3 install -r requirements.txt`

`python3 archivepodcast.py -c /path/to/settings.json`

## Settings.json

If there is no file that exists at the specified path it will create it, if there is no path specified it will use the current directory.

Multiple podcasts can be defined in the array.

Most fields can be left blank and will just be filled with the original values, podcasturl and podcastnameoneword are required. I'd recommend setting the 'podcastnewname' value to indicate that the feed is a mirror/archive.

## TODO

Redo whole readme with new selfhosted version
production mode
unbreak root logging