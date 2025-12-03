"""Main function, for running adhoc."""

import argparse
from pathlib import Path

from . import run_ap_adhoc
from .utils import logger as ap_logger
from .utils.log_messages import log_intro


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
