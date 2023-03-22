#!/usr/bin/env python3

# Python script to archive and re-host Podcasts
# I hate XML

from downloadpodcast import *

import argparse
import logging
import xml.etree.ElementTree as Et
import os
# from sys import platform
# from datetime import datetime
# from urllib.error import HTTPError


debug = False

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

nginxinstructionsone = "\nlocation = /rss/"

nginxinstructionstwo = """ {
    ### override content-type ##
    types { } default_type "application/rss+xml; charset=utf-8";

    ## override header (more like send custom header using nginx) ##
    add_header x-robots-tag "noindex, nofollow";
}"""


def make_folder_structure(settingsjson):
    permissionserror = False
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
        except PermissionError:
            permissionserror = True
            logging.info("You do not have permission to create folder: " + folder)

    # Create robots.txt, do a delete and remake to catch potential permissions errors that will make the script fail later
    robotstxtpath = ''
    try:
        robotstxtpath = settingsjson['webroot'] + 'robots.txt'
        try:
            os.remove(robotstxtpath)
        except FileNotFoundError:
            logging.info("Creating: " + robotstxtpath)
        robotstxtfile = None
        robotstxtfile = open(robotstxtpath, "w")
        robotstxtfile.write("User-agent: *\nDisallow: /")
        robotstxtfile.close()
    except PermissionError:
        permissionserror = True
        logging.info("You do not have permission to create file: " + robotstxtpath)

    if permissionserror:
        logging.info("Run this this script as a different user. ex: nginx, apache, root")
        exit(1)





def create_html(settingsjson):
    logging.info("\033[47m\033[30mGenerating HTML\033[0m")
    htmlstring = ""
    htmlstring = htmlstring + websitepartone
    htmlstring = htmlstring + settingsjson['webpagetitle']
    htmlstring = htmlstring + websiteparttwo
    htmlstring = htmlstring + "<h1>" + settingsjson['webpagetitle'] + "</h1>\n"
    htmlstring = htmlstring + "<p>" + \
        settingsjson['webpagedescription'] + "</p>\n"
    htmlstring = htmlstring + '<p>For instructions on how to add a podcast url to a podcast app, <a href="' + \
        settingsjson['webpagepodcastguidelink'] + \
        '">check out this helpful guide</a>.</p>\n'
    for podcast in settingsjson['podcast']:
        htmlstring = htmlstring + "<h2>" + \
            podcast['podcastnewname'] + "</h2>\n"
        htmlstring = htmlstring + "<p>" + \
            podcast['podcastdescription'] + "</p>\n"
        podcasturl = settingsjson['inetpath'] + \
            "rss/" + podcast['podcastnameoneword']
        htmlstring = htmlstring + '<p><a href="' + \
            podcasturl + '">' + podcasturl + '</a></p>\n'

    htmlstring = htmlstring + websitepartthree

    logging.info('Writing HTML: ' + settingsjson['webroot'] + 'index.html')
    indexhtmlfile = None
    indexhtmlfile = open(settingsjson['webroot'] + 'index.html', "w")
    indexhtmlfile.write(htmlstring)
    indexhtmlfile.close()

    logging.info("Make sure to set this in the server{} section of nginx.conf:")
    for podcast in settingsjson['podcast']:
        logging.info(nginxinstructionsone +
              podcast['podcastnameoneword'] + nginxinstructionstwo)

    logging.info("Done!")


def main(args):
    # grab settings from settings.json, json > xml
    settingsjson = get_settings(args)

    # make the folder structure in the webroot if it doesnt already exist
    make_folder_structure(settingsjson)

    # download all the podcasts
    for podcast in settingsjson['podcast']:
        tree = download_podcasts(settingsjson)
        if tree:
            tree.write(settingsjson['webroot'] + 'rss/' + podcast['podcastnameoneword'], encoding='utf-8', xml_declaration=True)
        else:
            logging.info("XML Write Failure")

    # generate the html for the webroot
    create_html(settingsjson)


if __name__ == "__main__":
    print("\033[47m\033[30madhocarchive.py\033[0m")
    parser = argparse.ArgumentParser(description='Mirror / rehost a podcast')
    parser.add_argument('-c', type=str, dest='settingspath', help='Config path /path/to/settings.json')
    parser.add_argument('--debug', dest='debug', action='store_true', help='Show debug output')
    args = parser.parse_args()

    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(format='%(levelname)s:%(message)s', level=loglevel) #TODO FIXME TODO FIXME

    logging.debug("Script args: " + str(args))
    main(args)