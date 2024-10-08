#!/usr/bin/env python3
"""Self hosted podcast archiver"""

# 🐍 Standard Modules
import datetime
import logger
import os
import signal
import sys
import threading
import time
import xml.etree.ElementTree as Et

# 🐍 Pip
import boto3
from flask import (
    Blueprint,
    Flask,
    Response,
    redirect,
    render_template,
    send_from_directory,
)
from jinja2 import Environment, FileSystemLoader
from podcastargparser import create_arg_parser
from podcastlogger import setup_logger

# 🐍 Local, archivepodcast
from podcastsettings import get_settings
from waitress import serve

parser = create_arg_parser()
args = parser.parse_args()
setup_logger(args)

# Weird place to have an import, we need the logger running first
# 🐍 Local, archivepodcast
from archivepodcast.ap_downloader import download_podcasts  # pylint: disable=wrong-import-position

# 🌏 Globals
app = Flask(__name__, static_folder="static")  # Flask app object
PODCASTXML = {}
settingsjson = None
s3 = None
s3pathscache = []
aboutpage = False

# --- Why do I program like this, we are done with imports and vars


def reload_settings(signalNumber, frame):
    """Handle Sighup"""
    global settingsjson
    settingserror = False
    logger.debug("Handle Sighup %s %s", signalNumber, frame)
    logger.info("🙋 Got SIGHUP, Reloading Config")

    try:
        settingsjson = get_settings(args)
    except (FileNotFoundError, ValueError):
        settingserror = True
        logger.error("❌ Reload failed, keeping old config")

    try:
        make_folder_structure()
    except PermissionError:
        settingserror = True
        logger.error("❌ Failure creating new folder structure")

    if not settingserror:
        logger.info("🙋 Loaded config successfully!")
        grab_podcasts()  # No point grabbing podcasts adhoc if loading the config fails

    upload_static()  # Ensure the static files are updated (inetaddress change)

    logger.info("🙋 Finished adhoc config reload")


def upload_static():
    """Function to upload static to s3 and copy index.html"""
    get_s3_credential()

    # Check if about.html exists, affects index.html so it's first.
    if os.path.exists(settingsjson["webroot"] + os.sep + "about.html"):
        global aboutpage
        aboutpage = True
        logger.debug("Aboutpage exists!")

    # Render backup of html
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("templates/home.j2")
    rendered_output = template.render(settingsjson=settingsjson, aboutpage=aboutpage)

    with open(settingsjson["webroot"] + os.sep + "index.html", "w", encoding="utf-8") as rootwebpage:
        rootwebpage.write(rendered_output)

    if settingsjson["storagebackend"] == "s3":
        logger.info("⛅ Uploading static pages to s3 in the background")
        try:
            for item in [
                "/clipboard.js",
                "/favicon.ico",
                "/podcasto.css",
                "/fonts/fira-code-v12-latin-600.woff2",
                "/fonts/fira-code-v12-latin-700.woff2",
                "/fonts/noto-sans-display-v10-latin-500.woff2",
            ]:
                s3.upload_file("static" + item, settingsjson["s3bucket"], "static" + item)

            if aboutpage:
                s3.upload_file(
                    settingsjson["webroot"] + os.sep + "about.html",
                    settingsjson["s3bucket"],
                    "about.html",
                )

            s3.put_object(
                Body=rendered_output,
                Bucket=settingsjson["s3bucket"],
                Key="index.html",
                ContentType="text/html",
            )

            s3.put_object(
                Body="User-Agent: *\nDisallow: /\n",
                Bucket=settingsjson["s3bucket"],
                Key="robots.txt",
                ContentType="text/plain",
            )

            logger.info("⛅ Done uploading static pages to s3")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("⛅❌ Unhandled s3 Error: %s", exc)


if __name__ == "__main__":
    signal.signal(signal.SIGHUP, reload_settings)

    logger.info("🙋 Starting selfhostarchive.py strong, unphased.")
    logger.info("🙋 Podcast Archive running! PID: %s", os.getpid())

    settingsjson = get_settings(args)
    make_folder_structure()

    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting due to KeyboardInterrupt! 👋")
        sys.exit(130)
