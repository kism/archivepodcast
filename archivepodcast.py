#!/usr/bin/env python3

# I hate XML

import argparse
import requests
import xml.etree.ElementTree as Et
import urllib
import os
import json

debug = False
imageformats = ['.webp', '.png', '.jpg', '.jpeg', '.gif']

# A default settings config to be written to the file system if none exists at the expected path
defaultjson = """
{
    "webpagetitle": "Podcast Archive",
    "inetpath": "http://localhost/",
    "webroot": "output/",
    "podcast": [
        {
            "podcasturl": "",
            "podcastnewname": "",
            "podcastnameoneword": "",
            "podcastdescription": "",
            "contactemail": ""
        }
    ]
}
"""

websitepartone = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>"""
    
websiteparttwo = """</title>
    <meta http-equiv="X-Clacks-Overhead" content="GNU Terry Pratchett" />
  </head>

  <style>
    body {
    font-family: "Noto Sans Display", -apple-system, BlinkMacSystemFont,
        "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif, "Apple Color Emoji",
        "Segoe UI Emoji", "Segoe UI Symbol";
    font-size: 18px;
    font-weight: 500;
    background-color: rgb(26, 26, 26);
    color: rgb(200, 200, 200);
    line-height: 1.5;
    }
    h1,
    h2 {
    font-family: "Fira Code", "Consolas", "Lucida Console", monospace;
    line-height: 1.2;
    color: rgb(220, 220, 220);
    }
    h1 {
    font-size: 40px;
    font-weight: 700;
    margin: 20px 0 16px;
    }
    h2 {
    font-size: 24px;
    font-weight: 600;
    margin: 20px 0 16px;
    }
    p {
    margin: 0;
    margin-bottom: 16px;
    margin-top: -8px;
    }
    a:link {
    color: rgb(0, 128, 128);
    }
    a:visited {
    color: rgb(128, 0, 64);
    }
  </style>

  <body>
    <main>"""
websitepartthree = """    </main>
  </body>
</html>
"""

# Make sure to set this in the server{} section of nginx.conf

#        location = /rss/<podcastnameoneword> {
#           ## override content-type ##
#           types { } default_type "application/rss+xml; charset=utf-8";
#
#           ## override header (more like send custom header using nginx) #
#           add_header x-robots-tag "noindex, nofollow";
#        }


def print_debug(text):  # Debug messages in yellow if the debug global is true
    if debug:
        print("\033[93m" + text + "\033[0m")


def get_settings(args):  # Load settings from settings.json
    settingsjson = None
    settingserror = False

    settingspath = ''

    if args.settingspath:
        settingspath = args.settingspath
    else:
        settingspath = "settings.json"

    try:
        settingsjsonfile = open(settingspath, "r")
    except:  # If settings.json doesn't exist, create it based on the template defined earlier
        print("Settings json doesnt exist at: " + settingspath)
        print("Creating empty config, please fill it out.\n")
        settingsjsonfile = open(settingspath, "w")
        settingsjsonfile.write(defaultjson)
        settingsjsonfile.close()
        settingsjsonfile = open(settingspath, "r")

    try:
        settingsjson = json.loads(settingsjsonfile.read())
    except:
        print("Malformed json in settings.json, check the syntax")
        exit(1)

    settingsjsonfile.close()

    try:
        # Iterate through the default settings json in this file, if any of the keys arent in settings.json throw an error
        for setting in json.loads(defaultjson).keys():
            if settingsjson[setting] == '':
                settingserror = True
                print(setting + " not set")

    except KeyError:
        settingserror = True
        print("Looks like settings.json doesnt match the expecting schema format, make a backup, remove the original file, run the script again and have a look at the default settings.json file")

    if settingserror:
        print("Invalid config exiting, check " + settingspath)
        exit(1)

    return settingsjson


def make_folder_structure(settingsjson):
    folders = []
    folders.append(settingsjson['webroot'])
    folders.append(settingsjson['webroot'] + '/rss')
    folders.append(settingsjson['webroot'] + '/content')

    for entry in settingsjson['podcast']:
        folders.append(settingsjson['webroot'] +
                       '/content/' + entry['podcastnameoneword'])

    for folder in folders:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass


# Standardise naming, fix everything that could cause something to be borked on the file system or in a url
def cleanup_file_name(filename):
    filename = filename.encode('ascii', 'ignore')
    filename = filename.decode()

    # Standardise
    filename = filename.replace('[AUDIO]', '')
    filename = filename.replace('[Audio]', '')
    filename = filename.replace('[audio]', '')
    filename = filename.replace('AUDIO', '')
    filename = filename.replace('Ep ', 'Ep. ')
    filename = filename.replace('Ep: ', 'Ep. ')
    filename = filename.replace('Episode ', 'Ep. ')
    filename = filename.replace('Episode: ', 'Ep. ')
    # Filesystem
    filename = filename.replace('?', ' ')
    filename = filename.replace('\\', ' ')
    filename = filename.replace('/', ' ')
    filename = filename.replace(':', ' ')
    filename = filename.replace('*', ' ')
    filename = filename.replace('"', ' ')
    filename = filename.replace('<', ' ')
    filename = filename.replace('>', ' ')
    filename = filename.replace('(', ' ')
    filename = filename.replace(')', ' ')
    filename = filename.replace('|', ' ')
    # HTML / HTTP
    filename = filename.replace('&', ' ')
    filename = filename.replace("'", ' ')
    filename = filename.replace("_", ' ')
    filename = filename.replace("[", ' ')
    filename = filename.replace("]", ' ')
    filename = filename.replace(".", ' ')
    filename = filename.replace("#", ' ')
    filename = filename.replace(";", ' ')

    while '  ' in filename:
        filename = filename.replace('  ', ' ')

    filename = filename.strip()
    filename = filename.replace(' ', '-')

    print_debug('\033[92mClean Filename\033[0m: ' + "'" + filename + "'")
    return filename


# Download asset from url with appropiate file name
def download_asset(url, title, settingsjson, podcast, extension=''):
    filepath = settingsjson['webroot'] + 'content/' + \
        podcast['podcastnameoneword'] + '/' + title + extension

    if not os.path.isfile(filepath):  # if the asset hasn't already been downloaded
        if True:
            try:
                headers = {'user-agent': 'Mozilla/5.0'}
                r = requests.get(url, headers=headers)
                with open(filepath, 'wb') as f:
                    f.write(r.content)

                print("  \033[92mSuccess!\033[0m")
            except urllib.error.HTTPError as err:
                print("  \033[91mDownload Failed\033[0m" + ' ' + str(err))

    else:
        print("Already downloaded: " + title + extension)


def download_podcasts(settingsjson):
    for podcast in settingsjson['podcast']:
        response = None

        # lets fetch the original podcast xml
        request = podcast['podcasturl']

        try:
            response = requests.get(request, timeout=5)
        except:
            print("Real early failure on grabbing the podcast xml, weird")
            exit(1)

        if response is not None:
            if response.status_code != 200 and response.status_code != 400:
                print("Not a great web request, we got: " +
                    str(response.status_code))
                exit(1)
            else:
                print_debug("We got a pretty real response by the looks of it")
                print_debug(str(response))
        else:
            print("Failure, no sign of a response.")
            print_debug(
                "Probably an issue with the code. Not patreon catching onto you pirating a premium podcast.")
            exit(1)

        # We have the xml
        podcastxml = Et.fromstring(response.content)
        print_debug(str(podcastxml))

        xmlfirstchild = podcastxml[0]

        # It's time to iterate through the lad, we overwrite as necessary from the settings in settings.json
        title = ''
        url = ''

        for channel in xmlfirstchild:  # Dont complain
            print("\n\033[47m\033[30m Found XML item \033[0m")

            if channel.tag == 'link':
                print("Podcast link: " + channel.text)
                channel.text = settingsjson['inetpath']

            elif channel.tag == 'title':
                print("Podcast title: " + channel.text)
                channel.text = podcast['podcastnewname']

            elif channel.tag == 'description':
                print("Podcast description: " + channel.text)
                channel.text = podcast['podcastdescription']

            elif channel.tag == '{http://www.w3.org/2005/Atom}link':
                channel.attrib['href'] = settingsjson['inetpath'] + \
                    'rss/' + podcast['podcastnameoneword']
                channel.text = ' '  # here me out...

            elif channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}owner':
                for child in channel:
                    if child.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}name':
                        child.text = podcast['podcastnewname']
                    if child.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}email':
                        child.text = podcast['contactemail']

            elif channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}author':
                channel.text = podcast['podcastnewname']

            elif channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}image':
                title = podcast['podcastnewname']
                title = cleanup_file_name(title)
                url = channel.attrib.get('href')

                for filetype in imageformats:
                    if filetype in url:
                        print("Downloading: " + url)
                        download_asset(url, title, settingsjson, podcast, filetype)
                        channel.attrib['href'] = settingsjson['inetpath'] + \
                            'content/' + title + filetype

                channel.text = ' '

            elif channel.tag == 'image':
                for child in channel:
                    if child.tag == 'title':
                        print("Title: " + child.text)
                        child.text = podcast['podcastnewname']

                    elif child.tag == 'link':
                        child.text = settingsjson['inetpath']

                    elif child.tag == 'url':
                        title = podcast['podcastnewname']
                        title = cleanup_file_name(title)
                        url = child.text

                        for filetype in imageformats:
                            if filetype in url:
                                download_asset(
                                    url, title, settingsjson, podcast, filetype)
                                child.text = settingsjson['inetpath'] + 'content/' + \
                                    podcast['podcastnameoneword'] + \
                                    '/' + title + filetype
                        else:
                            print("Skipping non image file:" + title)

                    else:
                        print_debug('Unhandled XML tag: ' +
                                    child.tag + ' Leaving as-is')

                channel.text = ' '  # here me out...

            elif channel.tag == 'item':
                for child in channel:

                    if child.tag == 'title':
                        title = str(child.text)
                        print("Title: " + title)

                    elif child.tag == 'enclosure':
                        title = cleanup_file_name(title)
                        url = child.attrib.get('url')
                        if '.mp3' in url:
                            download_asset(url, title, settingsjson,
                                        podcast, '.mp3')
                        else:
                            url = ''
                            print("Skipping non-mp3 file:" + title)

                        child.text = settingsjson['inetpath'] + 'content/' + \
                            podcast['podcastnameoneword'] + \
                            '/' + title + '.mp3'

                    else:
                        print_debug('Unhandled XML tag: ' +
                                    child.tag + ' Leaving as-is')

            else:
                print_debug('Unhandled XML tag: ' +
                            channel.tag + ' Leaving as-is')

        podcastxml[0] = xmlfirstchild

        tree = Et.ElementTree(podcastxml)
        Et.register_namespace('googleplay', 'http://www.google.com/schemas/play-podcasts/1.0')
        Et.register_namespace('atom',       'http://www.w3.org/2005/Atom')
        Et.register_namespace('itunes',     'http://www.itunes.com/dtds/podcast-1.0.dtd')

        tree.write(settingsjson['webroot'] + 'rss/' +
                podcast['podcastnameoneword'], encoding='utf-8', xml_declaration=True)

def create_html(settingsjson):
    htmlstring = ""
    htmlstring = htmlstring + websitepartone
    htmlstring = htmlstring + settingsjson['webpagetitle']
    htmlstring = htmlstring + websiteparttwo

    htmlstring = htmlstring + "<h1>" + settingsjson['webpagetitle'] + "</h1>\n"

    for podcast in settingsjson['podcast']:
         htmlstring = htmlstring + "<h2>" + podcast['podcastnewname'] + "</h2>\n"
         htmlstring = htmlstring + "<p>" + settingsjson['inetpath'] + "rss/" + podcast['podcastnameoneword'] + "</p>\n"
        
    htmlstring = htmlstring + websitepartthree
    
    print_debug('\nWriting HTML')
    print_debug(htmlstring)

    print(settingsjson['webroot'] + 'index.html')
    indexhtmlfile = None
    indexhtmlfile = open(settingsjson['webroot'] + 'index.html', "w")
    indexhtmlfile.write(htmlstring)
    indexhtmlfile.close()


def main(args):
    # grab settings from settings.json, json > xml
    settingsjson = get_settings(args)

    # make the folder structure in the webroot if it doesnt already exist
    make_folder_structure(settingsjson)

    # download all the podcasts
    download_podcasts(settingsjson)

    # download all the podcasts
    create_html(settingsjson)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mirror / rehost a podcast')
    parser.add_argument('-c', type=str, dest='settingspath',
                        help='Config path /path/to/settings.json')
    parser.add_argument('--debug', dest='debug',
                        action='store_true', help='Show debug output')
    args = parser.parse_args()

    debug = args.debug
    print_debug(str(args))

    main(args)
