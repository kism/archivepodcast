#!/usr/bin/env python3

# I hate XML

import requests
import xml.etree.ElementTree as Et
import urllib
import os
import sys
import json

debug = True
imageformats = ['.webp', '.png', '.jpg', '.jpeg', '.gif']

defaultjson = """
{
    "podcasturl": "",
    "podcastnewname": "",
    "webroot": ""
}
"""


def print_debug(text):  # Debug messages in yellow if the debug global is true
    if debug:
        print("\033[93m" + text + "\033[0m")


def get_settings():
    settingsjson = None
    settingserror = False

    try:
        settingsjsonfile = open("settings.json", "r")
    except:
        settingsjsonfile = open("settings.json", "w")
        settingsjsonfile.write(defaultjson)
        settingsjsonfile.close()
        settingsjsonfile = open("settings.json", "r")

    settingsjson = json.loads(settingsjsonfile.read())

    settingsjsonfile.close()

    if settingsjson['podcasturl'] == '':
        settingserror = True
        print("podcasturl not set")

    if settingsjson['podcastnewname'] == '':
        settingserror = True
        print("podcastnewname not set")

    if settingsjson['webroot'] == '':
        settingserror = True
        print("webroot not set")

    if settingserror:
        print("Invalid config exiting, check settings.json")
        exit(1)

    return settingsjson


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
    filename = filename.replace('Ep ', 'Ep. ')
    filename = filename.replace('Ep: ', 'Ep. ')
    filename = filename.replace('Episode ', 'Ep. ')
    filename = filename.replace('Episode: ', 'Ep. ')

    while '  ' in filename:
        filename = filename.replace('  ', ' ')

    filename = filename.strip()

    print_debug('\033[92mClean Filename\033[0m: ' + "'" + filename + "'")
    return filename


def download_asset(url, title, settingsjson, extension=''):
    filepath = settingsjson['webroot'] + title + extension

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

    settingsjson = get_settings()

    request = settingsjson['podcasturl']

    try:
        response = requests.get(request, timeout=5)
    except:
        pass

    if response is not None:
        if response.status_code != 200 and response.status_code != 400:
            print("Not a great web request, we got: " +
                  str(response.status_code))
            exit(1)
        else:
            print_debug("We got a pretty real response by the looks of it")
            print_debug(str(response))
            failure = False
    else:
        print("Failure, no sign of a response.")
        print_debug(
            "Probably an issue with the code. Not patreon catching onto you pirating a premium podcast.")
        exit(1)

    podcastxml = Et.fromstring(response.content)
    print(podcastxml)

    xmlfirstchild = podcastxml[0]

    # It's time to iterate
    title = ''
    url = ''

    for channel in xmlfirstchild:  # Dont complain
        print_debug("\nNew Entry")
        print_debug(str(channel))
        print(str(channel.tag) + ': ' +
              str(channel.text) + ' ' + str(channel.attrib))

        if channel.tag == 'title':
            title = str(channel.text)
            print_debug("WE HERE: " + title)

        for child in channel:
            # print_debug(str(child))
            print(str(child.tag) + ': ' +
                  str(child.text) + ' ' + str(child.attrib))

            if child.tag == 'title':
                title = str(child.text)

            if child.tag == 'url':
                title = cleanup_episode_name(title)
                url = child.text

                for filetype in imageformats:
                    if filetype in url:
                        download_asset(url, title, settingsjson, filetype)
                else:
                    print("Skipping non image file:" + title)

            if child.tag == 'enclosure':
                title = cleanup_episode_name(title)
                url = child.attrib.get('url')
                if '.mp3' in url:
                    download_asset(url, title, settingsjson, '.mp3')
                else:
                    print("Skipping non-mp3 file:" + title)

    podcastxml[0] = xmlfirstchild

    tree = Et.ElementTree(podcastxml)
    tree.write(settingsjson['webroot'] + "output.xml")

    if failure is True:
        exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and (sys.argv[1] == "-d" or sys.argv[1] == "--debug"):
        debug = True
    main()
