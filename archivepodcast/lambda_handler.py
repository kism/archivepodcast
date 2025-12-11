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
LOCAL_RO_INSTANCE_PATH = Path("/opt/instance")
INSTANCE_PATH = Path("/tmp/instance")


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

    if not LOCAL_RO_INSTANCE_PATH.exists():
        msg = f"Instance path does not exist, please add via a layer to {LOCAL_RO_INSTANCE_PATH}"
        logger.error(msg)
        raise FileNotFoundError(msg)
    if not (LOCAL_RO_INSTANCE_PATH / "config.json").is_file():
        msg = f"Instance config.json not found in {LOCAL_RO_INSTANCE_PATH}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    shutil.copytree(src=LOCAL_RO_INSTANCE_PATH, dst=INSTANCE_PATH, dirs_exist_ok=True)
    run_ap_adhoc(instance_path=INSTANCE_PATH)
