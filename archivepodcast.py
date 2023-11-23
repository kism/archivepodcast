#!/usr/bin/env python3
"""Self hosted podcast archiver"""

import xml.etree.ElementTree as Et
import time
import datetime
import os
import sys
import threading
import logging
import signal

from flask import Flask, render_template, Blueprint, Response, send_from_directory
from waitress import serve

from podcastsettings import get_settings
from podcastargparser import create_arg_parser
from podcastlogging import setup_logger

parser = create_arg_parser()
args = parser.parse_args()
setup_logger(args)

# Weird place to have an import, we need the logger running first
from podcastdownload import download_podcasts  # pylint: disable=wrong-import-position

app = Flask(__name__, static_folder="static")  # Flask app object
PODCASTXML = {}
settingsjson = None

# --- Why do I program like this, we are done with imports and vars

@app.route("/")
def home():
    """Flask Home"""
    return render_template("home.j2", settingsjson=settingsjson)


@app.errorhandler(404)
# pylint: disable=unused-argument
def invalid_route(e):
    """404 Handler"""
    returncode = 404
    return (
        render_template(
            "error.j2",
            errorcode=str(returncode),
            errortext="Page not found, how did you even?",
            settingsjson=settingsjson,
        ),
        returncode,
    )


@app.route("/rss/<string:feed>", methods=["GET"])
def rss(feed):
    """Send RSS Feed"""
    logging.debug("Sending xml feed: %s", feed)
    xml = ""
    returncode = 200
    try:
        xml = PODCASTXML[feed]
    except TypeError:
        returncode = 500
        return (
            render_template(
                "error.j2",
                errorcode=str(returncode),
                errortext="The developer probably messed something up",
                settingsjson=settingsjson,
            ),
            returncode,
        )
    except KeyError:
        try:
            tree = Et.parse(settingsjson["webroot"] + "rss/" + feed)
            xml = Et.tostring(
                tree.getroot(),
                encoding="utf-8",
                method="xml",
                xml_declaration=True,
            )
            logging.warning("Feed not live, sending cached version")

        except FileNotFoundError:
            returncode = 404
            return (
                render_template(
                    "error.j2",
                    errorcode=str(returncode),
                    errortext="Feed not found, you know you can copy and paste yeah?",
                    settingsjson=settingsjson,
                ),
                returncode,
            )
    return Response(xml, mimetype="application/rss+xml; charset=utf-8")


@app.route("/robots.txt")
def static_from_root():
    """Serve robots.txt"""
    response = Response(
        response="User-Agent: *\nDisallow: /\n", status=200, mimetype="text/plain"
    )
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@app.route("/favicon.ico")
def favicon():
    """Return the favicon"""
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


def make_folder_structure():
    """Ensure that webbroot folder structure exists"""
    logging.debug("Checking folder structure")
    folders = []

    folders.append(settingsjson["webroot"])
    folders.append(settingsjson["webroot"] + os.sep + "rss")
    folders.append(settingsjson["webroot"] + os.sep + "content")

    for entry in settingsjson["podcast"]:
        folders.append(
            settingsjson["webroot"]
            + os.sep
            + "content"
            + os.sep
            + entry["podcastnameoneword"]
        )

    for folder in folders:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass
        except PermissionError as exc:
            err = "You do not have permission to create folder: " + folder
            logging.error(err)
            logging.error(
                "Run this this script as a different user probably. ex: nginx, apache, root"
            )
            raise PermissionError(err) from exc


def grab_podcasts():
    """Loop through defined podcasts, download and store the xml"""
    for podcast in settingsjson["podcast"]:
        tree = None
        logging.info("Processing settings entry: %s", podcast["podcastnewname"])

        rssfilepath = settingsjson["webroot"] + "rss/" + podcast["podcastnameoneword"]

        if podcast["live"] is True:  # download all the podcasts
            try:
                tree = download_podcasts(podcast, settingsjson)
                # Write xml to disk
                tree.write(
                    rssfilepath,
                    encoding="utf-8",
                    xml_declaration=True,
                )
                logging.debug("Wrote rss to disk: %s", rssfilepath)

            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.error(str(exc))
                logging.error(
                    "RSS XML Download Failure, attempting to host cached version"
                )
                tree = None
        else:
            logging.info('"live": false, in settings so not fetching new episodes')

        # Serving a podcast that we can't currently download?, load it from file
        if tree is None:
            logging.info("Loading rss from file: %s", rssfilepath)
            try:
                tree = Et.parse(rssfilepath)
            except FileNotFoundError:
                logging.error("Cannot find rss xml file: %s", rssfilepath)

        if tree is not None:
            PODCASTXML.update(
                {
                    podcast["podcastnameoneword"]: Et.tostring(
                        tree.getroot(),
                        encoding="utf-8",
                        method="xml",
                        xml_declaration=True,
                    )
                }
            )
            logging.info(
                "Hosted: %srss/%s",
                settingsjson["inetpath"],
                podcast["podcastnameoneword"],
            )
        else:
            logging.error("Unable to host podcast, something is wrong")


def podcast_loop():
    """Main loop, grabs new podcasts every hour"""
    time.sleep(
        3
    )  # lol, this is because I want the output to start after the web server comes up
    logging.info("Startup complete, looking for podcast episodes")

    while True:
        # We do a broad try/except here since god knows what http errors seem to happen at random
        # If there is something uncaught in the grab podcasts function it will crash the scraping
        # part of this program and it will need to be restarted, this avoids it.
        try:
            grab_podcasts()
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            logging.error(str(exc))

        # Calculate time until next run
        now = datetime.datetime.now()
        seconds_until_next_run = (3600 + 1200) - ((now.minute * 60) + now.second)
        if seconds_until_next_run > 3600:
            seconds_until_next_run -= 3600

        logging.info("Sleeping for ~%s minutes", str(int(seconds_until_next_run / 60)))
        time.sleep(seconds_until_next_run)
        logging.info("Waking up, looking for new episodes")


def reload_settings(signalNumber, frame):
    """Handle Sighup"""
    global settingsjson
    settingserror = False
    logging.debug("Handle Sighup %s %s", signalNumber, frame)
    logging.info("Got SIGHUP, Reloading Config")

    try:
        settingsjson = get_settings(args)
    except (FileNotFoundError, ValueError):
        settingserror = True
        logging.error("Reload failed, keeping old config")

    try:
        make_folder_structure()
    except PermissionError:
        settingserror = True
        logging.error("Failure creating new folder structure")

    if not settingserror:
        logging.info("Loaded config successfully!")
        grab_podcasts()  # No point grabbing podcasts adhoc if loading the config fails

    logging.info("Finished adhoc config reload")


def main():
    """Main, globals have been defined"""

    # Start Thread
    thread = threading.Thread(target=podcast_loop, daemon=True)
    thread.start()

    # Finish Creating App
    blueprint = Blueprint(
        "site",
        __name__,
        static_url_path="/content",
        static_folder=settingsjson["webroot"] + "/content",
    )
    app.register_blueprint(blueprint)

    logging.info("Webapp address: http://%s:%s", args.webaddress, args.webport)
    if args.production:
        # Maybe use os.cpu_count() ?
        logging.info("Starting webapp in production mode (waitress)")
        serve(app, host=args.webaddress, port=args.webport, threads=16)
    else:  # Run with the flask debug service
        logging.info("Starting webapp in debug mode (werkzeug)")
        app.run(host=args.webaddress, port=args.webport)

    print("\nWebapp Stopped\nPress ^C (again) to exit")

    # Cleanup
    thread.join()


if __name__ == "__main__":
    signal.signal(signal.SIGHUP, reload_settings)

    logging.info("Starting selfhostarchive.py strong, unphased.")
    logging.info("Self Hosted Podcast Archive running! PID: %s", os.getpid())

    settingsjson = get_settings(args)
    make_folder_structure()

    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting due to KeyboardInterrupt! 👋")
        sys.exit(130)
