# archivepodcast.py

This Python script 

## How to do

`git clone https://github.com/kism/archivepodcast.git`

`cd archivepodcast`

`pip3 install requests`

`python3 archivepodcast.py -c /path/to/settings.json`

## Settings.json

If there is no file that exists at the specified path it will create it, if there is no path specified it will use the current directory.

Multiple podcasts can be defined in the array.

Most fields can be left blank and will just be filled with the original values, podcasturl and podcastnameoneword are required. I'd recommend setting the 'podcastnewname' value to indicate that the feed is a mirror/archive.


