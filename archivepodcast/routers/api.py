"""API routes for ArchivePodcast."""

import signal
from http import HTTPStatus

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from archivepodcast.instances.health import health
from archivepodcast.instances.podcast_archiver import (
    get_ap,
    reload_config,
)
from archivepodcast.instances.profiler import event_times
from archivepodcast.utils.health import PodcastArchiverHealthAPI
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.profiler import EventLastTime

logger = get_logger(__name__)
router = APIRouter(tags=["api"])


@router.get("/api/reload")
def api_reload() -> JSONResponse:
    """Reload the config."""
    if not get_ap().debug:
        return JSONResponse({"msg": "Config reload not allowed in production"}, status_code=HTTPStatus.FORBIDDEN)

    reload_config(signal.SIGHUP)

    return JSONResponse({"msg": "Config reload command sent"})


@router.get("/api/health", response_model=PodcastArchiverHealthAPI)
def api_health() -> JSONResponse:
    """Health check."""
    try:
        health_json = health.get_health().model_dump()
    except Exception:
        logger.exception("Error getting health")
        health_json = {"core": {"alive": False}}

    return JSONResponse(health_json)


@router.get("/api/profile", response_model=EventLastTime)
def api_profile() -> EventLastTime:
    """Get the profiling info as JSON."""
    return event_times
