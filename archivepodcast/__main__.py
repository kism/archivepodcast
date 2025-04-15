"""Main function, for running adhoc."""

import argparse
import logging
import time
from pathlib import Path

from . import __version__
from . import logger as ap_logger
from .ap_archiver import PodcastArchiver
from .config import DEFAULT_LOGGING_CONFIG, ArchivePodcastConfig

INSTANCE_PATH = Path.cwd() / "instance"  # Default instance path for the app


def main(config_dict: dict | ArchivePodcastConfig | None = None, instance_path: Path | None = None) -> None:
    """Main for adhoc running."""
    if not instance_path:
        instance_path = INSTANCE_PATH

    ap_conf = config_dict if config_dict else ArchivePodcastConfig(instance_path=instance_path)

    ap_logger.setup_logger(app=None, logging_conf=ap_conf["logging"])  # Setup logger with config

    logger = ap_logger.get_logger(__name__)

    debug = False
    if logger.getEffectiveLevel() <= logging.DEBUG:
        debug = True

    ap = PodcastArchiver(
        app_config=ap_conf["app"],
        podcast_list=ap_conf["podcast"],
        instance_path=INSTANCE_PATH,
        root_path=Path.cwd(),
        debug=debug,
    )

    ap.grab_podcasts()

    logger.info("Waiting for html rendering to finish...")

    while ap.health.core.currently_rendering:
        time.sleep(0.1)

    logger.info("Done!")


if __name__ == "__main__":
    start_time = time.time()
    ap_logger.setup_logger(
        app=None, logging_conf=DEFAULT_LOGGING_CONFIG
    )  # Setup logger with defaults defined in config module

    parser = argparse.ArgumentParser(description="Archivepodcast.")
    parser.add_argument(
        "--instance_path",
        type=str,
        default="",
        help="Path to the instance directory.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="",
        help="Path to the config file.",
    )
    args = parser.parse_args()

    instance_path = Path(args.instance_path) if args.instance_path else INSTANCE_PATH

    if args.config:
        config_dict = ArchivePodcastConfig(instance_path=instance_path, config=None, config_file_path=Path(args.config))

    main(config_dict=config_dict, instance_path=instance_path)
    logger = ap_logger.get_logger(__name__)
    logger.info("🙋 ArchivePodcast Version: %s adhoc ran in %.2f seconds.", __version__, time.time() - start_time)
