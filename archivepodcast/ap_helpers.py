from flask import current_app

from .logger import get_logger

import os

logger = get_logger(__name__)

about_page = True


def initialise_archivepodcast():
    """Initialize the archivepodcast app"""
    make_folder_structure()


def make_folder_structure():
    """Ensure that webbroot folder structure exists"""
    logger.debug("Checking folder structure")

    app_settings = current_app.config["app"]
    folders = []

    folders.append(current_app.instance_path)
    folders.append(os.path.join(current_app.instance_path, "rss"))
    folders.append(os.path.join(current_app.instance_path, "content"))

    for entry in app_settings["podcasts"]:
        folders.append(os.path.join(current_app.instance_path, "content", entry["name_one_word"]))

    for folder in folders:
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass
        except PermissionError as exc:
            emoji = "❌"  # un-upset black
            err = emoji + " You do not have permission to create folder: " + folder
            logger.exception(
                "%s Run this this script as a different user probably, or check permissions of the webroot.",
                emoji,
            )
            raise PermissionError(err) from exc
