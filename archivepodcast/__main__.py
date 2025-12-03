"""Main function, for running adhoc."""

import argparse
import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .archiver import PodcastArchiver
from .instances.config import get_ap_config
from .instances.health import health
from .instances.path_helper import get_app_paths
from .instances.profiler import event_times
from .utils import logger as ap_logger
from .utils.log_messages import log_intro

if TYPE_CHECKING:
    from archivepodcast.utils.profiler import EventLastTime  # pragma: no cover
else:
    EventLastTime = object


DEFAULT_INSTANCE_PATH = Path.cwd() / "instance"  # Default instance path for the app


def _get_times_recursive(event: EventLastTime, indent: int = 0) -> str:
    """Get the event times recursively for printing."""
    if event.name == "/":
        event.name = "root"
    msg = " " * indent + f"{event.name}: "
    if event.duration is not None:
        msg += f"{event.duration.total_seconds():.2f}s\n"
    else:
        msg += "No duration\n"
    if event.children is not None:
        for child in event.children:
            msg += _get_times_recursive(child, indent + 2)
    return msg


def get_event_times_str() -> str:
    """Print the event times to the logger."""
    msg = "Event times, async so anything can be held up by anything else in a pool >>>\n"
    msg += _get_times_recursive(event_times, indent=1)
    if msg.split("\n")[-1] == "":
        msg = "\n".join(msg.split("\n")[:-1])
    return msg


def run_ap_adhoc(
    instance_path: Path | None = None,
    config_path: Path | None = None,
) -> None:
    """Main for adhoc running."""
    logger = ap_logger.get_logger(__name__)

    start_time = time.time()
    if not instance_path:
        msg = f"Instance path not provided, using default: {DEFAULT_INSTANCE_PATH}"
        logger.info(msg)
        instance_path = DEFAULT_INSTANCE_PATH  # pragma: no cover # This avoids issues in PyTest
        if not instance_path.exists():
            msg = f"Instance path ({instance_path}) does not exist, not creating it for safety."
            raise FileNotFoundError(msg)

    if not config_path:
        config_path = instance_path / "config.json"

    ap_conf = get_ap_config(config_path=config_path)

    ap_logger.setup_logger(app=None, logging_conf=ap_conf.logging)  # Setup logger with config

    podcast_archiver_start_time = time.time()

    get_app_paths(root_path=Path.cwd(), instance_path=instance_path)

    ap = PodcastArchiver(
        app_config=ap_conf.app,
        podcast_list=ap_conf.podcasts,
        debug=False,  # The debug of the ap object is only for the Flask web server
    )
    event_times.set_event_time("PodcastArchiver", time.time() - podcast_archiver_start_time)

    ap.grab_podcasts()
    asyncio.run(ap.write_health_s3())
    event_times.set_event_time("/", time.time() - start_time)

    logger.trace(health.get_health().model_dump_json(indent=4))
    logger.trace(event_times.model_dump_json(indent=4))
    logger.info(get_event_times_str())
    logger.info("Done!")


def main() -> None:
    """Main function for CLI."""
    ap_logger.setup_logger(app=None)  # Setup logger with defaults defined in config module

    logger = ap_logger.get_logger(__name__)
    log_intro("adhoc", logger)

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


if __name__ == "__main__":
    main()  # pragma: no cover
