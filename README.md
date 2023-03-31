# archivepodcast.py

This is a python project that both
* Works as an adhoc way to archive a podcast from a RSS feed
* Works as a Flask webapp to archive and re-host a podcast from a RSS feed

In theory this works in windows however I havent tested it, it ~should be able to handle windows file paths fine.

## Setup

`git clone https://github.com/kism/archivepodcast.git`

`cd archivepodcast`

`python3 -m venv env`

`source env/bin/activate`

`pip3 install -r requirements.txt`

If you want to convert WAV episodes to mp3, ensure that you have ffmpeg installed and the program will handle it automatically.

## Settings.json

If there is no file that exists at the specified path it will create it, if there is no path specified it will use the current directory.

Multiple podcasts can be defined in the array.

Most fields can be left blank and will just be filled with the original values, podcasturl and podcastnameoneword are required. I'd recommend using the 'podcastnewname' value to change the name to something that would indicate that your feed is an archive.

### Global Settings
`"webpagetitle"` The Webpage Title

`"webpagedescription"` The text under the title of the webpage

`"webpagepodcastguidelink"` A link to a guide on adding rss manually to a podcast app, the generatated default has one that I like prefilled.

`"inetpath"` The url of the server, in the case of running the flask version it will be `"http://localhost:5000/"`

`"webroot"` The folder to download to and serve the podcast files from
* If using standalone version set this to your nginx webroot
* If using the standalone version set this to whichever folder you want

### Podcast Settings
In an array called podcast, there is an object per podcast for the options

`"podcasturl"` The URL of the podcast feed you want to archive

`"podcastnewname"` The new name of the podcast as it will appear in a podcast app

`"podcastnameoneword"` the folder name for the podcast, keep it short and just use alphas

`"podcastdescription"` The new description of the podcast as it will appear in a podcast app

`"live"` Whether the podcast will updated every hour, or just served from the archived rss feed

`"contactemail"` Override the contact email of the podcast


## Running Adhoc Script to backup a podcast

This will...

`python3 adhocarchive.py --help` will get you all the arguements that you should know about.

`python3 adhocarchive.py -c settings.json`

## Running the standalone version to archive and re-host the podcast

This will...

`python3 selfhostarchive.py --help` will get you all the arguements that you should know about.

`python3 selfhostarchive.py -c settings.json --production`





## TODO

* ~~flask version~~
* ~~nice copy button with javascript~~
* ~~log to file~~
* ~~fix logging~~
* Redo whole readme with new selfhosted version
* ~~production mode~~
* ~~do monitoring~~
* ~~check that logging without logfile still works~~
* ~~more safety when handling containers, failure might reveal original URL~~
* ~~hotreaload settings.json~~
* ~~& and other symbol safety in the html~~
* ~~be okay with no value for url in settings if reading the archiveed rss~~
* ~~add fonts~~
* ~~fix error handling on reading settings file~~
* ~~url safety for images~~
