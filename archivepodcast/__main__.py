"""Main function, for running adhoc."""

import argparse
import time
from pathlib import Path

from .archiver import PodcastArchiver
from .instances.config import get_ap_config
from .utils import logger as ap_logger
from .version import __version__

DEFAULT_INSTANCE_PATH = Path.cwd() / "instance"  # Default instance path for the app


def run_ap_adhoc(
    instance_path: Path | None = None,
    config_path: Path | None = None,
) -> None:
    """Main for adhoc running."""
    logger = ap_logger.get_logger(__name__)
    if not instance_path:
        msg = f"Instance path not provided, using default: {DEFAULT_INSTANCE_PATH}"
        logger.warning(msg)
        instance_path = DEFAULT_INSTANCE_PATH  # pragma: no cover # This avoids issues in PyTest
        if not instance_path.exists():
            msg = f"Instance path ({instance_path}) does not exist, not creating it for safety."
            raise FileNotFoundError(msg)

    ap_conf = get_ap_config(config_path=config_path)

    ap_logger.setup_logger(app=None, logging_conf=ap_conf.logging)  # Setup logger with config

    ap = PodcastArchiver(
        app_config=ap_conf.app,
        podcast_list=ap_conf.podcasts,
        instance_path=instance_path,
        root_path=Path.cwd(),
        debug=False,  # The debug of the ap object is only for the Flask web server
    )

    ap.grab_podcasts()

    logger.info("Waiting for html rendering to finish...")

    while ap.health.currently_rendering():
        time.sleep(0.05)

    logger.info("Done!")


def main() -> None:
    """Main function for CLI."""
    start_time = time.time()
    ap_logger.setup_logger(app=None)  # Setup logger with defaults defined in config module

    logger = ap_logger.get_logger(__name__)
    logger.info("🙋 ArchivePodcast Version: %s running adhoc", __version__)

    parser = argparse.ArgumentParser(description="Archivepodcast.")
    parser.add_argument(
        "--instance-path",
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

    instance_path = Path(args.instance_path) if args.instance_path else None
    config_path = Path(args.config) if args.config else None

    run_ap_adhoc(instance_path=instance_path, config_path=config_path)

    logger.info("🙋 ArchivePodcast ran adhoc in %.2f seconds", time.time() - start_time)


if __name__ == "__main__":
    main()  # pragma: no cover
