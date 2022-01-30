#!/usr/bin/env python3

# I hate XML

import requests
import xml.etree.ElementTree as Et
import urllib
import os
import sys
import json

debug = False
imageformats = ['.webp', '.png', '.jpg', '.jpeg', '.gif']

defaultjson = """
{
    "podcasturl": "",
    "podcastnewname": "",
    "podcastnameoneword": "",
    "podcastdescription": "",
    "inetpath": "http://localhost/",
    "webroot": "output/",
    "contactemail": "bootleg@localhost"
}
"""

# Make sure to set this in the server{} section of nginx.conf

#        location = /rss/<podcastnameoneword> {
#           ## override content-type ##
#           types { } default_type "application/atom+xml; charset=utf-8";
#
#           ## override header (more like send custom header using nginx) #
#           add_header x-robots-tag "noindex, nofollow";
#        }

def print_debug(text):  # Debug messages in yellow if the debug global is true
    if debug:
        print("\033[93m" + text + "\033[0m")


def get_settings(): # Load settings from settings.json
    settingsjson = None
    settingserror = False

    try:
        settingsjsonfile = open("settings.json", "r")
    except: # If settings.json doesn't exist, create it based on the template defined earlier
        settingsjsonfile = open("settings.json", "w")
        settingsjsonfile.write(defaultjson)
        settingsjsonfile.close()
        settingsjsonfile = open("settings.json", "r")

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
        print("Invalid config exiting, check settings.json")
        exit(1)

    return settingsjson

def make_folder_structure(settingsjson):
    folders = []
    folders.append(settingsjson['webroot'])
    folders.append(settingsjson['webroot'] + '/rss')
    folders.append(settingsjson['webroot'] + '/content')

    for folder in folders:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass

def cleanup_episode_name(filename): # Standardise naming, fix everything that could cause something to be borked on the file system or in a url
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
    # HTML
    filename = filename.replace('&', ' ')
    filename = filename.replace("'", ' ')
    filename = filename.replace("_", ' ')
    filename = filename.replace("[", ' ')
    filename = filename.replace("]", ' ')
    filename = filename.replace(".", ' ')

    while '  ' in filename:
        filename = filename.replace('  ', ' ')

    filename = filename.strip()
    filename = filename.replace(' ', '-')

    print_debug('\033[92mClean Filename\033[0m: ' + "'" + filename + "'")
    return filename


def download_asset(url, title, settingsjson, extension=''): # Download asset from url with appropiate file name
    filepath = settingsjson['webroot'] + 'content/' + title + extension

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
        print("Already downloaded: " + title)


def main():
    response = None

    settingsjson = get_settings() # grab settings from settings.json, json > xml

    make_folder_structure(settingsjson) # make the folder structure in the webroot if it doesnt already exist

    # lets fetch the original podcast xml
    request = settingsjson['podcasturl'] 

    try:
        response = requests.get(request, timeout=5)
    except:
        print("Real early failure on grabbing the podcast xml, weird")
        exit(1)

    if response is not None:
        if response.status_code != 200 and response.status_code != 400:
            print("Not a great web request, we got: " + str(response.status_code))
            exit(1)
        else:
            print_debug("We got a pretty real response by the looks of it")
            print_debug(str(response))
            failure = False
    else:
        print("Failure, no sign of a response.")
        print_debug("Probably an issue with the code. Not patreon catching onto you pirating a premium podcast.")
        exit(1)

    # We have the xml
    podcastxml = Et.fromstring(response.content)
    print_debug(str(podcastxml))

    xmlfirstchild = podcastxml[0]

    # It's time to iterate through the lad, we overwrite as necessary from the settings in settings.json
    title = ''
    url = ''

    for channel in xmlfirstchild:  # Dont complain
        print("\n - Found XML item -")
        print_debug(str(channel))
        print_debug(str(channel.tag) + ': ' + str(channel.text) + ' ' + str(channel.attrib))

        if channel.tag == 'link':
            channel.text = settingsjson['inetpath']

        if channel.tag == 'title':
            channel.text = settingsjson['podcastnewname']

        if channel.tag == 'description':
            channel.text = settingsjson['podcastdescription']

        if channel.tag == '{http://www.w3.org/2005/Atom}link':
            channel.attrib['href'] = settingsjson['inetpath'] + 'rss/' + settingsjson['podcastnameoneword']
            channel.text = ' '  # here me out...

        if channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}owner':
            for child in channel:
                if child.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}name':
                    child.text = settingsjson['podcastnewname']
                if child.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}email':
                    child.text = settingsjson['contactemail']

        if channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}author':
            channel.text = settingsjson['podcastnewname']

        if channel.tag == '{http://www.itunes.com/dtds/podcast-1.0.dtd}image':
            title = settingsjson['podcastnewname']
            title = cleanup_episode_name(title)
            url = channel.attrib.get('href')

            for filetype in imageformats:
                if filetype in url:
                    download_asset(url, title, settingsjson, filetype)
                    channel.attrib['href'] = settingsjson['inetpath'] + 'content/' + title + filetype

            channel.text = ' '

        if channel.tag == 'image':
            for child in channel:
                if child.tag == 'title':
                    child.text = settingsjson['podcastnewname']
                if child.tag == 'link':
                    child.text = settingsjson['inetpath']
                if child.tag == 'url':
                    title = settingsjson['podcastnewname']
                    title = cleanup_episode_name(title)
                    url = child.text

                    for filetype in imageformats:
                        if filetype in url:
                            download_asset(url, title, settingsjson, filetype)
                            child.text = settingsjson['inetpath'] + \
                                'content/' + title + filetype
                    else:
                        print("Skipping non image file:" + title)                        

            channel.text = ' '  # here me out...

        if channel.tag == 'item':
            for child in channel:
                # print_debug(str(child))
                print_debug(str(child.tag) + ': ' + str(child.text) + ' ' + str(child.attrib))

                if child.tag == 'title':
                    title = str(child.text)

                if child.tag == 'description':
                    child.text = settingsjson['podcastdescription']

                if child.tag == 'enclosure':
                    title = cleanup_episode_name(title)
                    url = child.attrib.get('url')
                    if '.mp3' in url:
                        download_asset(url, title, settingsjson, '.mp3')
                    else:
                        url = ''
                        print("Skipping non-mp3 file:" + title)

                    child.attrib['url'] = settingsjson['inetpath'] + 'content/' + \
                        title + '.mp3'

    podcastxml[0] = xmlfirstchild

    tree = Et.ElementTree(podcastxml)
    Et.register_namespace('googleplay', 'http://www.google.com/schemas/play-podcasts/1.0')
    Et.register_namespace('atom', 'http://www.w3.org/2005/Atom')
    Et.register_namespace('itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')

    tree.write(settingsjson['webroot'] + 'rss/' + settingsjson['podcastnameoneword'], encoding='utf-8', xml_declaration=True)

    if failure is True:
        exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and (sys.argv[1] == "-d" or sys.argv[1] == "--debug"):
        debug = True
    main()
