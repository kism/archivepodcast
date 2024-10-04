
import datetime
import time

import threading
from flask import current_app

from .logger import get_logger

import os

logger = get_logger(__name__)

about_page = True


def initialise_archivepodcast() -> None:
    """Initialize the archivepodcast app."""
    make_folder_structure()
    """Main, globals have been defined"""

    # Start thread: podcast backup loop
    thread = threading.Thread(target=podcast_loop, daemon=True)
    thread.start()

    # Start thread: upload static (wastes time otherwise, doesn't affect anything)
    # thread = threading.Thread(target=upload_static, daemon=True) # TODO: NOT IMPLEMENTED
    # thread.start()

    # Cleanup
    thread.join()


def make_folder_structure() -> None:
    """Ensure that webbroot folder structure exists"""
    logger.debug("Checking folder structure")

    app_settings = current_app.config["app"]
    folders = []

    folders.append(current_app.instance_path)
    folders.append(os.path.join(current_app.instance_path, "rss"))
    folders.append(os.path.join(current_app.instance_path, "content"))

    folders.extend(
        os.path.join(current_app.instance_path, "content", entry["name_one_word"]) for entry in app_settings["podcasts"]
    )

    for folder in folders:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass
        except PermissionError as exc:
            emoji = "❌"
            err = emoji + " You do not have permission to create folder: " + folder
            logger.exception(
                "%s Run this this script as a different user probably, or check permissions of the webroot.",
                emoji,
            )
            raise PermissionError(err) from exc


def podcast_loop():
    """Main loop, grabs new podcasts every hour"""
    time.sleep(3)  # lol, this is because I want the output to start after the web server comes up
    get_s3_credential()
    logger.info("" + "🙋 Starting podcast loop: grabbing episodes, building rss feeds. Repeating hourly.")

    if settingsjson["storagebackend"] == "s3":
        emoji = "⛅"  # un-upset black
        logger.info(
            "%s Since we are in s3 storage mode, the first iteration of checking which episodes are downloaded will be slow",
            emoji,
        )

    while True:
        # We do a broad try/except here since god knows what http errors seem to happen at random
        # If there is something uncaught in the grab podcasts function it will crash the scraping
        # part of this program and it will need to be restarted, this avoids it.
        try:
            grab_podcasts()
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            logger.error("❌ Error that broke grab_podcasts(): %s", str(exc))

        # Calculate time until next run
        now = datetime.datetime.now()
        seconds_until_next_run = (3600 + 1200) - ((now.minute * 60) + now.second)
        if seconds_until_next_run > 3600:
            seconds_until_next_run -= 3600

        emoji = "🛌"  # un-upset black
        logger.info("%s Sleeping for ~%s minutes", emoji, str(int(seconds_until_next_run / 60)))
        time.sleep(seconds_until_next_run)
        logger.info("🌄 Waking up, looking for new episodes")
