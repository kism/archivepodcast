#!/usr/bin/env python3
"""Self hosted podcast archiver"""
import xml.etree.ElementTree as Et
import argparse
import time
import threading
import logging

from flask import Flask, render_template, Blueprint, Response

from downloadpodcast import get_settings, download_podcasts


app = Flask(__name__, static_folder="static")  # Flask app object
PODCASTXML = {}


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


def podcastloop():
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


def main():
    """Main, globals have been defined"""
    # Start Thread
    thread = threading.Thread(
        target=podcastloop,
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
    app.run(host=args.WEBADDRESS, port=args.WEBPORT)

    # Cleanup
    thread.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mirror / rehost a podcast, self hoasted with Flask!"
    )
    parser.add_argument(
        "-wa",
        "--webaddress",
        type=str,
        dest="WEBADDRESS",
        help="(WebUI) Web address to listen on, default is 0.0.0.0",
        default="0.0.0.0",
    )
    parser.add_argument(
        "-wp",
        "--webport",
        type=int,
        dest="WEBPORT",
        help="(WebUI) Web port to listen on, default is 5000",
        default=5000,
    )
    parser.add_argument(
        "-c", type=str, dest="settingspath", help="Config path /path/to/settings.json"
    )
    parser.add_argument(
        "--debug", dest="debug", action="store_true", help="Show debug output"
    )
    args = parser.parse_args()

    LOGLEVEL = logging.INFO
    if args.debug:
        LOGLEVEL = logging.DEBUG
    logging.basicConfig(format="%(levelname)s:%(message)s", level=LOGLEVEL)

    args = parser.parse_args()

    settingsjson = get_settings(args)

    main()
