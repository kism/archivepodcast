"""Blueprint for Content Serving and RSS Feeds."""

from http import HTTPStatus
from pathlib import Path

from flask import Blueprint, Response, current_app, redirect, send_from_directory
from werkzeug.wrappers.response import Response as WerkzeugResponse

from archivepodcast.instances.config import get_ap_config
from archivepodcast.instances.podcast_archiver import (
    get_ap,
)
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)
bp = Blueprint("content", __name__)


@bp.route("/content/<path:path>")  # type: ignore[untyped-decorator]
def send_content(path: str) -> Response | WerkzeugResponse:
    """Serve Content."""
    ap = get_ap()

    ap_conf = get_ap_config()

    if ap_conf.app.storage_backend == "s3":
        path_obj = Path(path)
        web_root = Path(ap.web_root)
        relative_path = str(path_obj).replace(str(web_root), "")  # The easiest way to get the "relative" path
        new_path = ap_conf.app.s3.cdn_domain.encoded_string() + "content/" + relative_path
        return redirect(location=new_path, code=HTTPStatus.TEMPORARY_REDIRECT)

    web_dir = Path(current_app.instance_path) / "web" / "content"
    return send_from_directory(str(web_dir), path)
