"""Routes for serving archived podcast content."""

from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse

from archivepodcast.instances.config import get_ap_config
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.instances.podcast_archiver import generate_404
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)
bp = APIRouter(include_in_schema=False)


@bp.get("/content/{path:path}")
def send_content(path: str) -> Response:
    """Serve Content."""
    ap_conf = get_ap_config()

    if ap_conf.app.storage_backend == "s3":
        path_obj = Path(path)
        web_root = Path(get_app_paths().web_root)
        relative_path = str(path_obj).replace(str(web_root), "")  # The easiest way to get the "relative" path
        new_path = ap_conf.app.s3.cdn_domain.encoded_string() + "content/" + relative_path
        return RedirectResponse(new_path, status_code=HTTPStatus.TEMPORARY_REDIRECT)

    web_dir = (get_app_paths().instance_path / "web" / "content").resolve()
    file_path = (web_dir / path).resolve()
    if not file_path.is_relative_to(web_dir) or not file_path.is_file():
        return generate_404()

    return FileResponse(file_path)
