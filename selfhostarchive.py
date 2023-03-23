#!/usr/bin/env python3
from flask import Flask, render_template, Blueprint, Response
from downloadpodcast import *
import xml.etree.ElementTree as Et
import argparse
import time
import threading

app = Flask(__name__)  # Flask app object
podcastxml = {}


@app.route("/")
def home():  # Flask Home
    return render_template("home.j2", settingsjson=settingsjson)


@app.route("/rss/<string:feed>", methods=["GET"])
def rss(feed):
    logging.info("Sending xml feed: " + feed)
    xml = "no podcast here, check your url"
    try:
        xml = podcastxml[feed]
    except:
        pass
    return Response(xml, mimetype="application/rss+xml; charset=utf-8")


def podcastloop(settingsjson):
    global podcastxml
    tree = None
    while True:
        for podcast in settingsjson["podcast"]:
            if podcast["live"] == True:  # download all the podcasts
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
            else:  # If we are serving a podcast that is no longer being served "not live", load it from a file
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

            if tree != None:
                podcastxml.update(
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


def main(args, settingsjson):

    # Start Thread
    thread = threading.Thread(target=podcastloop, args=(settingsjson,))
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

    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(format="%(levelname)s:%(message)s", level=loglevel)

    args = parser.parse_args()

    settingsjson = get_settings(args)

    main(args, settingsjson)
