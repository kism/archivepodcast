"""Tests for downloader helpers."""

from typing import TYPE_CHECKING

from archivepodcast.downloader import helpers

if TYPE_CHECKING:
    import pytest


async def test_delay_download(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test delay_download sleeps without error."""
    monkeypatch.setattr(helpers.random, "uniform", lambda *_: 0)
    await helpers.delay_download(0)
