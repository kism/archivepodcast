# archivepodcast

This is a python project that both

- `archivepodcast.py` Works as a Flask webapp to archive and re-host a podcast from a RSS feed

In theory this works in windows however I havent tested it, it ~should be able to handle windows file paths fine.

## Setup

Install prereqs

```bash
apt install python-pipenv
dnf install python-pipenv
pacman -Syyu python-pipenv
```

Clone and create the pipenv

```bash
git clone https://github.com/kism/archivepodcast.git
cd archivepodcast
pipenv install --dev
pipenv shell
```

If you want to convert WAV episodes to mp3, ensure that you have ffmpeg installed and the program will handle it automatically.

## Settings.json

If there is no file that exists at the specified path it will create it, if there is no path specified it will use the current directory.

Multiple podcasts can be defined in the array.

Most fields can be left blank and will just be filled with the original values, podcasturl and podcastnameoneword are required. I'd recommend using the 'podcastnewname' value to change the name to something that would indicate that your feed is an archive.

### Global Settings

`"webpagetitle"` The Webpage Title

`"webpagedescription"` The text under the title of the webpage

`"webpagepodcastguidelink"` A link to a guide on adding rss manually to a podcast app, the generatated default has one that I like prefilled.

`"inetpath"`

- Required for building the xml rss feed.
- In the case of running the flask version locally it will be `"http://localhost:5000/"`, in a production environment it will be the websites url, ex: `"https://mycoolpodcastarchive.com/"`

`"webroot"` The folder to download to and serve the podcast files from

### Podcast Settings

In an array called podcast, there is an object per podcast for the options

`"podcasturl"` The URL of the podcast feed you want to archive

`"podcastnewname"` The new name of the podcast as it will appear in a podcast app

`"podcastnameoneword"` the folder name for the podcast, keep it short and just use alphas

`"podcastdescription"` The new description of the podcast as it will appear in a podcast app

`"live"` Whether the podcast will updated every hour, or just served from the archived rss feed

`"contactemail"` Override the contact email of the podcast

## Running archivepodcast webapp

This will run a webapp on <http://localhost:5000> (configurable) that will:

- Run persistently
- Host RSS feeds of the podcasts
- If `"live" : true` in settings json is set it will look for and download new episodes every hour
- If you send it a SIGHUP command it will reload the configuration, be sure to check the logs to see if it was successful.

`python3 archiveselfhost.py --help` will get you all the arguements that you should know about.

`python3 archiveselfhost.py -c settings.json --production`

An example guide on setting it up start to finish, with all features can be found here [here](README_examplesetup.md).

### TODO

- Update readme
- Copy robots.txt to s3
- Fix logic to not upload feeds to s3 every time
