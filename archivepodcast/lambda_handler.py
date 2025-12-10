"""Lambda Mode for running adhoc as a fun cron job."""

import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.data_classes import ALBEvent
    from aws_lambda_powertools.utilities.typing import LambdaContext
else:
    ALBEvent = object
    LambdaContext = object


# We don't use the real logger yet since we want to be able to diagnose import issues
logger = logging.getLogger()
logger.setLevel(logging.INFO)

LAMBDA_LIB_PATH = Path("/opt/lib")

try:
    from archivepodcast import run_ap_adhoc
    from archivepodcast.downloader.helpers import check_ffmpeg  # noqa: F401 # For checking in the aws console
    from archivepodcast.utils.log_messages import log_intro

except ImportError:
    logger.error("Failed to import archivepodcast module")
    logger.error("Contents of %s: %s", LAMBDA_LIB_PATH, [str(p) for p in LAMBDA_LIB_PATH.iterdir()])
    raise


if "LD_LIBRARY_PATH" in os.environ:
    os.environ["LD_LIBRARY_PATH"] = f"{LAMBDA_LIB_PATH}:{os.environ['LD_LIBRARY_PATH']}"
else:
    os.environ["LD_LIBRARY_PATH"] = str(LAMBDA_LIB_PATH)

# check_ffmpeg(convert_check=True)  # noqa: ERA001 # For checking in the aws console


def handler(event: ALBEvent, context: LambdaContext) -> None:
    # Copy the RO instance folder to /tmp/instance since it needs to be writable
    logger.info("Event invoked with event: %s", event)

    log_intro(logger)
    local_instance_path = Path("/opt/instance")
    instance_path = Path("/tmp/instance")

    if not local_instance_path.exists():
        msg = f"Instance path does not exist, please add via a layer to {local_instance_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)
    if not (local_instance_path / "config.json").is_file():
        msg = f"Instance config.json not found in {local_instance_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    shutil.copytree(src=local_instance_path, dst=instance_path, dirs_exist_ok=True)
    run_ap_adhoc(instance_path=instance_path)
