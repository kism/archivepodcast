"""Main function, for running adhoc."""

import argparse
from pathlib import Path

from . import run_ap_adhoc
from .constants import DEFAULT_INSTANCE_PATH
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

    args = parser.parse_args()

    instance_path = Path(args.instance_path) if args.instance_path else None

    if not instance_path:
        msg = f"Instance path not provided, using default: {DEFAULT_INSTANCE_PATH}"
        logger.info(msg)
        instance_path = DEFAULT_INSTANCE_PATH  # pragma: no cover # This avoids issues in PyTest
        if not instance_path.exists():
            msg = f"Instance path ({instance_path}) does not exist, not creating it for safety."
            raise FileNotFoundError(msg)

    run_ap_adhoc(instance_path=instance_path)


if __name__ == "__main__":
    main()  # pragma: no cover
