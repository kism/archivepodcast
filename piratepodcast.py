#!/usr/bin/env python3

# I hate XML

import requests
import xml.etree.ElementTree as ET
import urllib
import os
import sys

debug = True


def print_debug(text):  # Debug messages in yellow if the debug global is true
    if debug:
        print("\033[93m" + text + "\033[0m")


def cleanup_episode_name(filename):
    filename = filename.encode('ascii', 'ignore')
    filename = filename.decode()
    filename = filename.replace('?', ' ')
    filename = filename.replace('\\', ' ')
    filename = filename.replace('/', ' ')
    filename = filename.replace(':', ' ')
    filename = filename.replace('*', ' ')
    filename = filename.replace('"', ' ')
    filename = filename.replace('<', ' ')
    filename = filename.replace('>', ' ')
    filename = filename.replace('|', ' ')
    filename = filename.replace('[AUDIO]', '')
    filename = filename.replace('[Audio]', '')
    filename = filename.replace('[audio]', '')
    filename = filename.replace('Ep ',      'Ep. ')
    filename = filename.replace('Ep: ',     'Ep. ')
    filename = filename.replace('Episode ', 'Ep. ')
    filename = filename.replace('Episode: ', 'Ep. ')

    while '  ' in filename:
        filename = filename.replace('  ', ' ')

    filename = filename.strip()

    print_debug('\033[92mClean Filename\033[0m: ' + "'" + filename + "'")
    return filename


def download_misc(url, title):
    pass


def download_asset(url, title):
    filepath = "output/" + title + '.mp3'

    if not os.path.isfile(filepath):  # if the asset hasn't already been downloaded
        if True:
            try:
                podcastURL = url
                headers = {'user-agent': 'Mozilla/5.0'}
                r = requests.get(podcastURL, headers=headers)
                with open(filepath, 'wb') as f:
                    f.write(r.content)

                print("  \033[92mSuccess!\033[0m")
            except urllib.error.HTTPError as err:
                print("  \033[91mDownload Failed\033[0m" + ' ' + str(err))

    else:
        print("Already downloaded: " + title)


def main():
    response = None

    try:
        podcastfile = open("podcast.txt", "r")
    except:
        print('Gotta have a one line podcast.txt that has the premium podcast URL')
        exit(1)
    request = podcastfile.read().strip()
    print(request)

    try:
        os.mkdir("output")
    except FileExistsError:
        pass

    try:
        response = requests.get(request, timeout=5)
    except:
        pass

    if response != None:
        if response.status_code != 200 and response.status_code != 400:
            print("Not a great web request, we got: " +
                  str(response.status_code))
            failure = True
        else:
            print_debug("We got a pretty real response by the looks of it")
            print_debug(str(response))
            failure = False
    else:
        print("Failure, no sign of a responce.")
        print_debug(
            "Probably an issue with the code. Not patreon catching onto you pirating a premium podcast.")
        failure = True

    podcastxml = ET.fromstring(response.content)
    print(podcastxml)

    podcastxml = podcastxml[0]

    for channel in podcastxml:  # Dont complain
        print_debug("\nNew Entry")
        print_debug(str(channel))
        print(str(channel.tag) + ': ' +
                  str(channel.text) + ' ' + str(channel.attrib))
        
        title = ''
        url = ''

        if channel.tag == 'title':
            title = str(channel.text)
            print_debug("WE HERE: " + title)

        for child in channel:
            #print_debug(str(child))
            print(str(child.tag) + ': ' +
                  str(child.text) + ' ' + str(child.attrib))

            if child.tag == 'title':
                title = str(child.text)

            if child.tag == 'url':
                title = cleanup_episode_name(title)
                url = child.text
                if ('.jpg' in url) or ('.png' in url) or ('.webp' in url) or ('.jpeg' in url) or ('.gif' in url):
                    download_asset(child.attrib.get('url'), title)
                else:
                    print("Skipping non-mp3 file:" + title)

            if child.tag == 'enclosure':
                title = cleanup_episode_name(title)
                url = child.attrib.get('url')
                if '.mp3' in url:
                    download_asset(url, title)
                else:
                    print("Skipping non-mp3 file:" + title)


if __name__ == "__main__":
    if len(sys.argv) > 1 and (sys.argv[1] == "-d" or sys.argv[1] == "--debug"):
        debug = True
    main()
