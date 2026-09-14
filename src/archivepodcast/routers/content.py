"""Routes for serving archived podcast content."""

from http import HTTPStatus

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse

from archivepodcast.instances.config import get_ap_config
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.instances.podcast_archiver import generate_404
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(include_in_schema=False)


@router.get("/content/{path:path}")
def send_content(path: str) -> Response:
    """Serve Content."""
    ap_conf = get_ap_config()

    if ap_conf.app.storage_backend == "s3":
        new_path = ap_conf.app.s3.cdn_domain.encoded_string() + "content/" + path
        return RedirectResponse(new_path, status_code=HTTPStatus.TEMPORARY_REDIRECT)

    web_dir = (get_app_paths().instance_path / "web" / "content").resolve()
    file_path = (web_dir / path).resolve()
    if not file_path.is_relative_to(web_dir) or not file_path.is_file():
        return generate_404()

    return FileResponse(file_path)
