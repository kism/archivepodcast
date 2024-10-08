import datetime
import os
import threading
import time

from flask import current_app

from .ap_archiver import PodcastArchiver
from .logger import get_logger

logger = get_logger(__name__)

about_page = True
ap = None


def initialise_archivepodcast() -> None:
    """Initialize the archivepodcast app."""
    global ap  # noqa: PLW0603
    ap = PodcastArchiver(current_app.config["app"])

    # Start thread: podcast backup loop
    thread = threading.Thread(target=podcast_loop, daemon=True)
    thread.start()

    # Start thread: upload static (wastes time otherwise, doesn't affect anything)
    # thread = threading.Thread(target=upload_static, daemon=True) # TODO: NOT IMPLEMENTED
    # thread.start()

    # Cleanup
    thread.join()





def podcast_loop() -> None:
    """Main loop, grabs new podcasts every hour."""
    logger.info("🙋 Starting podcast loop: grabbing episodes, building rss feeds. Repeating hourly.")

    if ap is None:
        logger.error("❌ ArchivePodcast object not initialized")
        return

    if ap.s3 is not None:
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
            ap.grab_podcasts()
        except Exception:
            logger.exception("❌ Error that broke grab_podcasts()")

        # Calculate time until next run
        now = datetime.datetime.now()

        one_hour_in_seconds = 3600
        seconds_offset = 1200  # 20 minutes

        seconds_until_next_run = (one_hour_in_seconds + seconds_offset) - ((now.minute * 60) + now.second)
        if seconds_until_next_run > one_hour_in_seconds:
            seconds_until_next_run -= one_hour_in_seconds

        emoji = "🛌"  # un-upset black
        logger.info("%s Sleeping for ~%s minutes", emoji, str(int(seconds_until_next_run / 60)))
        time.sleep(seconds_until_next_run)
        logger.info("🌄 Waking up, looking for new episodes")
