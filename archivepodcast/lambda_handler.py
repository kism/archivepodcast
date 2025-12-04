"""Lambda Mode for running adhoc as a fun cron job."""

import logging
import shutil
from pathlib import Path
from typing import Any

from archivepodcast import run_ap_adhoc

logger = logging.getLogger()


def handler(event: Any, context: Any) -> None:  # noqa: ANN401, ARG001, D103
    # Copy the RO instance folder to /tmp/instance since it needs to be writable
    local_instance_path = Path("/opt/instance")
    instance_path = Path("/tmp/instance")  # noqa: S108

    if not local_instance_path.exists():
        logger.error("Instance path does not exist, please add via a layer to %s", str(local_instance_path))
        return
    if not (local_instance_path / "config.json").is_file():
        logger.error("Instance config.json not found in %s", str(local_instance_path))
        return

    shutil.copytree(local_instance_path, instance_path)
    run_ap_adhoc(instance_path=instance_path)
