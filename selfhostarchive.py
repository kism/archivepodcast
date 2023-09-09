#!/usr/bin/env python3
"""Self hosted podcast archiver"""

import xml.etree.ElementTree as Et
import argparse
import time
import datetime
import os
import sys
import threading
import logging
import signal

from flask import Flask, render_template, Blueprint, Response

try:
    from waitress import serve

    HASWAITRESS = True
except ImportError:
    HASWAITRESS = False

from downloadpodcast import get_settings, download_podcasts, setup_logger

print("Starting selfhostarchive.py strong, unphased.\n")

app = Flask(__name__, static_folder="static")  # Flask app object
PODCASTXML = {}
settingsjson = None


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


def make_folder_structure():
    """Ensure that webbroot folder structure exists"""
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
            err = ("You do not have permission to create folder: %s", folder)
            logging.error(err)
            logging.error(
                "Run this this script as a different user. ex: nginx, apache, root"
            )
            raise PermissionError(err) from exc


def grab_podcasts():
    """Loop through defined podcasts, download and store the xml"""
    tree = None
    for podcast in settingsjson["podcast"]:
        if podcast["live"] is True:  # download all the podcasts
            tree = download_podcasts(podcast, settingsjson)
            if tree:  # Write xml to disk
                tree.write(
                    settingsjson["webroot"] + "rss/" + podcast["podcastnameoneword"],
                    encoding="utf-8",
                    xml_declaration=True,
                )
            else:
                logging.error("XML Download Failure")
        else:  # Serving a podcast that we can't currently download?, load it from file
            try:
                tree = Et.parse(
                    settingsjson["webroot"] + "rss/" + podcast["podcastnameoneword"]
                )
            except FileNotFoundError:
                logging.error(
                    "Cannot find xml file "
                    + podcast["podcastnameoneword"]
                    + " at "
                    + settingsjson["webroot"]
                    + "rss/"
                    + podcast["podcastnameoneword"]
                )

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


def podcast_loop():
    """Main loop, grabs new podcasts every hour"""
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

    if args.production and HASWAITRESS:
        serve(app, host=args.webaddress, port=args.webport)
    else:  # Run with the flask debug service
        app.run(host=args.webaddress, port=args.webport)

    print("\nWebapp Stopped\nPress ^C (again) to exit")

    # Cleanup
    thread.join()


if __name__ == "__main__":
    signal.signal(signal.SIGHUP, reload_settings)

    parser = argparse.ArgumentParser(
        description="Mirror / rehost a podcast, self hoasted with Flask!"
    )
    parser.add_argument(
        "-wa",
        "--webaddress",
        type=str,
        dest="webaddress",
        help="(WebUI) Web address to listen on, default is 0.0.0.0",
        default="0.0.0.0",
    )
    parser.add_argument(
        "-wp",
        "--webport",
        type=int,
        dest="webport",
        help="(WebUI) Web port to listen on, default is 5000",
        default=5000,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        dest="settingspath",
        help="Config path /path/to/settings.json",
    )
    parser.add_argument(
        "--loglevel",
        type=str,
        dest="loglevel",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    parser.add_argument(
        "-lf",
        "--logfile",
        type=str,
        dest="logfile",
        help="Log file full path",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        dest="production",
        help="Run the server with waitress instead of flask debug server",
    )
    args = parser.parse_args()

    setup_logger(args)

    logging.info("Self Hosted Podcast Archive running! PID: %s", os.getpid())

    settingsjson = get_settings(args)
    make_folder_structure()

    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting due to KeyboardInterrupt! 👋")
        sys.exit(130)
