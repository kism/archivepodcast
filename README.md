# archivepodcast

This is a python project that both

- `archivepodcast.py` Works as a Flask webapp to archive and re-host a podcast from a RSS feed

In theory this works in windows however I haven't tested it, it ~should be able to handle windows file paths fine.

## Setup

Install dependencies

```bash

```

```bash

```

If you want to convert WAV episodes to mp3, ensure that you have ffmpeg installed and the program will handle it automatically.

## Settings.json

If there is no file that exists at the specified path it will create it, if there is no path specified it will use the current directory.

Multiple podcasts can be defined in the array.

Most fields can be left blank and will just be filled with the original values, url and name_one_word are required. I'd recommend using the 'new_name' value to change the name to something that would indicate that your feed is an archive.

### Global Settings

`"app.web_page.title"` The Webpage Title

`"app.web_page.description"` The text under the title of the webpage

`"app.web_page.podcast_guide"` A link to a guide on adding rss manually to a podcast app, the generated default has one that I like prefilled.

`"app.inet_path"`

- Required for building the xml rss feed.
- In the case of running the flask version locally it will be `"http://localhost:5000/"`, in a production environment it will be the websites url, ex: `"https://mycoolpodcastarchive.com/"`

TKTKTKTKTK INSTANCE PATH

### Podcast Settings

In an array called podcast, there is an object per podcast for the options

`"podcast.url"` The URL of the podcast feed you want to archive

`"podcast.new_name"` The new name of the podcast as it will appear in a podcast app

`"podcast.name_one_word"` the folder name for the podcast, keep it short and just use alphas

`"podcast.description"` The new description of the podcast as it will appear in a podcast app

`"podcast.live"` Whether the podcast will updated every hour, or just served from the archived rss feed

`"podcast.contact_email"` Override the contact email of the podcast

## Running archivepodcast webapp

This will run a webapp on <http://localhost:5000> (configurable) that will:

- Run persistently
- Host RSS feeds of the podcasts
- If `"live" : true` in settings json is set it will look for and download new episodes every hour
- If you send it a SIGHUP command it will reload the configuration, be sure to check the logs to see if it was successful.

`python3 <TKTKTKTKTK> --help` will get you all the arguments that you should know about.

`python3 TKTKTKTKTK.py -c settings.json --production`

An example guide on setting it up start to finish, with all features and saving episodes do disk can be found here [here](README_local.md). There are others for if you want to use s3 to host assets, or even host the whole thing on s3.

### TODO

- Docker
- Quick startup (s3 thread)
- Re-write README
- Quick docker build
