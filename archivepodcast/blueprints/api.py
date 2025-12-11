"""API blueprints for ArchivePodcast."""

import json
import signal
from http import HTTPStatus

from flask import Blueprint, Response

from archivepodcast.constants import JSON_INDENT
from archivepodcast.instances.health import health
from archivepodcast.instances.podcast_archiver import (
    get_ap,
    reload_config,
)
from archivepodcast.instances.profiler import event_times
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)
bp = Blueprint("api", __name__)


@bp.route("/api/reload")  # type: ignore[untyped-decorator]
def api_reload() -> Response:
    """Reload the config."""
    ap = get_ap()

    msg_success = {"msg": "Config reload command sent"}
    msg_forbidden = {"msg": "Config reload not allowed in production"}

    if not ap.debug:
        return Response(
            json.dumps(msg_forbidden),
            content_type="application/json; charset=utf-8",
            status=HTTPStatus.FORBIDDEN,
        )

    reload_config(signal.SIGHUP)

    return Response(
        json.dumps(msg_success),
        content_type="application/json; charset=utf-8",
        status=HTTPStatus.OK,
    )


@bp.route("/api/health")  # type: ignore[untyped-decorator]
def api_health() -> Response:
    """Health check."""
    try:
        health_json = health.get_health().model_dump()
        # Alphabetical json
        health_json_str = json.dumps(health_json, sort_keys=True, indent=JSON_INDENT)
    except Exception:
        logger.exception("Error getting health")
        health_json_str = json.dumps({"core": {"alive": False}}, sort_keys=True, indent=JSON_INDENT)

    return Response(
        health_json_str,
        mimetype="application/json",
        content_type="application/json; charset=utf-8",
        status=HTTPStatus.OK,
    )


@bp.route("/api/profile")  # type: ignore[untyped-decorator]
def api_profile() -> Response:
    """Get the profiling info as JSON."""
    profile_json_str = event_times.model_dump_json(indent=JSON_INDENT)

    return Response(
        profile_json_str,
        mimetype="application/json",
        content_type="application/json; charset=utf-8",
        status=HTTPStatus.OK,
    )
