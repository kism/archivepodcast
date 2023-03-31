#!/usr/bin/env python3
"""Self hosted podcast archiver"""
import xml.etree.ElementTree as Et
import argparse
import time
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


app = Flask(__name__, static_folder="static")  # Flask app object
PODCASTXML = {}
settingsjson = None


@app.route("/")
def home():
    """Flask Home"""
    return render_template("home.j2", settingsjson=settingsjson)


@app.route("/rss/<string:feed>", methods=["GET"])
def rss(feed):
    """Send RSS Feed"""
    logging.info("Sending xml feed: %s", feed)
    xml = "no podcast here, check your url"
    try:
        xml = PODCASTXML[feed]
    except TypeError:
        pass
    return Response(xml, mimetype="application/rss+xml; charset=utf-8")


@app.route("/robots.txt")
def static_from_root():
    """Serve robots.txt"""
    response = Response(
        response="User-Agent: *\nDisallow: /\n", status=200, mimetype="text/plain"
    )
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


def make_folder_structure():  # Eeeeehh TODO clean this up because lol robots.txt
    """Ensure that webbroot folder structure exists"""
    permissionserror = False
    folders = []
    folders.append(settingsjson["webroot"])
    folders.append(settingsjson["webroot"] + "/rss")
    folders.append(settingsjson["webroot"] + "/content")

    for entry in settingsjson["podcast"]:
        folders.append(
            settingsjson["webroot"] + "/content/" + entry["podcastnameoneword"]
        )

    for folder in folders:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass
        except PermissionError:
            permissionserror = True
            logging.info("You do not have permission to create folder: %s", folder)

    if permissionserror:
        logging.info(
            "Run this this script as a different user. ex: nginx, apache, root"
        )
        sys.exit(1)


def podcast_loop():
    """Loop through defined podcasts, download and store the xml"""

    tree = None
    while True:
        for podcast in settingsjson["podcast"]:
            if podcast["live"] is True:  # download all the podcasts
                tree = download_podcasts(podcast, settingsjson)
                if tree:  # Write xml to disk
                    tree.write(
                        settingsjson["webroot"]
                        + "rss/"
                        + podcast["podcastnameoneword"],
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

        logging.info("Sleeping")
        time.sleep(3600)


def reload_settings(signalNumber, frame):
    """Handle Sighup"""
    global settingsjson
    logging.debug("Handle Sighup %s %s", signalNumber, frame)

    settingsjson = get_settings(args)
    make_folder_structure()

    return


def main():
    """Main, globals have been defined"""

    # Start Thread
    thread = threading.Thread(
        target=podcast_loop,
    )
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
        help="Logging Level",
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

    settingsjson = get_settings(args)
    make_folder_structure()

    setup_logger(args)

    logging.info("Self Hosted Podcast Archive running! PID: %s", os.getpid())

    main()
