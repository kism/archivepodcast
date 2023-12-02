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

import boto3

# from botocore.exceptions import NoCredentialsError, ClientError

from jinja2 import Environment, FileSystemLoader

from flask import (
    Flask,
    render_template,
    Blueprint,
    Response,
    send_from_directory,
    redirect,
)
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
s3 = None
s3pathscache = []

# --- Why do I program like this, we are done with imports and vars


@app.route("/")
def home():
    """Flask Home"""
    return render_template("home.j2", settingsjson=settingsjson)

@app.route("/index.html")
def home():
    """Flask Home, s3 backup compatible"""
    # This ensures that if you transparently redirect / to /index.html
    # for using in cloudflare r2 storage it will work
    # If the vm goes down you can change the main domain dns to point to r2
    # and everything should work.
    return render_template("home.j2", settingsjson=settingsjson)

@app.route("/content/<path:path>")
def send_content(path):
    """Serve Content"""
    response = None

    if settingsjson["storagebackend"] == "s3":
        newpath = (
            settingsjson["cdndomain"]
            + "content/"
            + path.replace(settingsjson["webroot"], "")
        )
        response = redirect(newpath, code=302)
    else:
        response = send_from_directory(settingsjson["webroot"] + "/content", path)

    return response


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
    folders.append(settingsjson["webroot"] + "rss")
    folders.append(settingsjson["webroot"] + "content")

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
        previousfeed = ""
        logging.info("Processing settings entry: %s", podcast["podcastnewname"])

        try:  # If the var exists, we set it
            previousfeed = PODCASTXML[podcast["podcastnameoneword"]]
        except KeyError:
            pass

        rssfilepath = settingsjson["webroot"] + "rss/" + podcast["podcastnameoneword"]

        if podcast["live"] is True:  # download all the podcasts
            try:
                tree = download_podcasts(podcast, settingsjson, s3, s3pathscache)
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

            # Upload to s3 if we are in s3 mode
            if (
                settingsjson["storagebackend"] == "s3"
                and previousfeed != PODCASTXML[podcast["podcastnameoneword"]]
            ):
                try:
                    # Upload the file
                    s3.put_object(
                        Body=PODCASTXML[podcast["podcastnameoneword"]],
                        Bucket=settingsjson["s3bucket"],
                        Key="rss/" + podcast["podcastnameoneword"],
                        ContentType="application/rss+xml",
                    )
                    logging.info(
                        "Uploaded feed \"%s\" to s3", podcast["podcastnameoneword"]
                    )
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logging.error("Unhandled s3 Error: %s", exc)

        else:
            logging.error("Unable to host podcast, something is wrong")


def podcast_loop():
    """Main loop, grabs new podcasts every hour"""
    time.sleep(
        3
    )  # lol, this is because I want the output to start after the web server comes up
    logging.info("Startup complete, looking for podcast episodes")

    if settingsjson["storagebackend"] == "s3":
        logging.info(
            "Since we are in s3 storage mode, the first iteration of checking which episodes are downloaded will be slow"
        )

    while True:
        # We do a broad try/except here since god knows what http errors seem to happen at random
        # If there is something uncaught in the grab podcasts function it will crash the scraping
        # part of this program and it will need to be restarted, this avoids it.
        try:
            grab_podcasts()
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            logging.error("Error that broke grab_podcasts(): %s", str(exc))

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


def upload_static():
    """Function to upload static to s3 and copy index.html"""
    # Render backup of html
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("templates/home.j2")
    rendered_output = template.render(settingsjson=settingsjson)

    with open(
        settingsjson["webroot"] + os.sep + "index.html", "w", encoding="utf-8"
    ) as rootwebpage:
        rootwebpage.write(rendered_output)

    if settingsjson["storagebackend"] == "s3":
        logging.info("Uploading static pages to s3 in the background")
        try:
            for item in [
                "/clipboard.js",
                "/favicon.ico",
                "/podcasto.css",
                "/fonts/fira-code-v12-latin-600.woff2",
                "/fonts/fira-code-v12-latin-700.woff2",
                "/fonts/noto-sans-display-v10-latin-500.woff2",
            ]:
                s3.upload_file(
                    "static" + item, settingsjson["s3bucket"], "static" + item
                )

            s3.put_object(
                Body=rendered_output,
                Bucket=settingsjson["s3bucket"],
                Key="index.html",
                ContentType="text/html",
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logging.error("Unhandled s3 Error: %s", exc)

    logging.info("Done uploading static pages to s3")


def main():
    """Main, globals have been defined"""

    # Start thread: podcast backup loop
    thread = threading.Thread(target=podcast_loop, daemon=True)
    thread.start()

    # Start thread: upload static (wastes time otherwise, doesn't affect anything)
    thread = threading.Thread(target=upload_static, daemon=True)
    thread.start()

    # Finish Creating App
    blueprint = Blueprint(
        "site",
        __name__,
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
    logging.info("Podcast Archive running! PID: %s", os.getpid())

    settingsjson = get_settings(args)
    make_folder_structure()

    if settingsjson["storagebackend"] == "s3":
        s3 = boto3.client(
            "s3",
            endpoint_url=settingsjson["s3apiurl"],
            aws_access_key_id=settingsjson["s3accesskeyid"],
            aws_secret_access_key=settingsjson["s3secretaccesskey"],
        )

    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting due to KeyboardInterrupt! 👋")
        sys.exit(130)
