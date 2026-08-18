"""Adhoc (one-shot) archive run for ArchivePodcast."""

import asyncio
import time
from pathlib import Path

from .archiver import PodcastArchiver
from .constants import JSON_INDENT
from .instances.config import get_ap_config
from .instances.health import health
from .instances.path_helper import get_app_paths
from .instances.profiler import event_times
from .utils import logger as ap_logger
from .utils.profiler import get_event_times_str


def run_ap_adhoc(
    instance_path: Path,
) -> None:
    """Main for adhoc running."""
    logger = ap_logger.get_logger(__name__)

    start_time = time.time()

    config_path = instance_path / "config.json"

    ap_conf = get_ap_config(config_path=config_path)
    ap_conf.write_config(config_path)
    ap_conf.log_info(running_adhoc=True)

    ap_logger.setup_logger(logging_conf=ap_conf.logging)  # Setup logger with config

    podcast_archiver_start_time = time.time()

    get_app_paths(root_path=Path.cwd(), instance_path=instance_path)

    ap = PodcastArchiver(
        app_config=ap_conf.app,
        podcast_list=ap_conf.podcasts,
        debug=False,  # The debug of the ap object is only for the web server
    )
    event_times.set_event_time("PodcastArchiver", time.time() - podcast_archiver_start_time)

    ap.grab_podcasts()
    asyncio.run(ap.write_health_s3())
    event_times.set_event_time("/", time.time() - start_time)

    logger.trace(health.get_health().model_dump_json(indent=JSON_INDENT))
    logger.trace(event_times.model_dump_json(indent=JSON_INDENT))
    logger.info(get_event_times_str(event_times))
    logger.info("Done!")
