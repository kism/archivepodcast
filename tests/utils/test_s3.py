"""Tests for s3 helpers."""

from archivepodcast.utils.s3 import cache_control_for


def test_cache_control_for() -> None:
    """Immutable assets get a year, everything else stays short."""
    assert cache_control_for("content/ep1.mp3") == "public, max-age=31536000"
    assert cache_control_for("static/fonts/x.woff2") == "public, max-age=31536000"
    assert cache_control_for("static/health.js") == "public, max-age=180"
    assert cache_control_for("rss/podcast") == "public, max-age=180"
