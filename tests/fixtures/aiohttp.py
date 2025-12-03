from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import pytest

from tests.constants import TEST_RSS_LOCATION, TEST_WAV_FILE
from tests.models.aiohttp import FakeResponseDef, FakeSession

if TYPE_CHECKING:
    from aiohttp.pytest_plugin import AiohttpServer
    from pytest_mock import MockerFixture  # pragma: no cover
else:
    MockerFixture = object
    AiohttpServer = object


@pytest.fixture
async def mock_podcast_source_rss_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a podcast definition from the config."""

    filepath = Path(TEST_RSS_LOCATION) / "test_valid.rss"

    with filepath.open() as file:
        rss = file.read()

    responses: dict[str, FakeResponseDef] = {
        "https://pytest.internal/rss/test_source": {"data": rss, "status": 200},
        "https://pytest.internal/images/test.jpg": {"data": b"jpg", "status": 200},
        "https://pytest.internal/audio/test.mp3": {"data": b"mp3", "status": 200},
    }

    def fake_session(*args: Any, **kwargs: Any) -> FakeSession:
        return FakeSession(responses=responses)

    monkeypatch.setattr(aiohttp, "ClientSession", fake_session)


@pytest.fixture
async def mock_podcast_source_rss_no_episodes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a podcast definition from the config."""

    filepath = Path(TEST_RSS_LOCATION) / "test_valid_no_episodes.rss"

    with filepath.open() as file:
        rss = file.read()

    responses: dict[str, FakeResponseDef] = {
        "https://pytest.internal/rss/test_source": {"data": rss, "status": 200},
    }

    def fake_session(*args: Any, **kwargs: Any) -> FakeSession:
        return FakeSession(responses=responses)

    monkeypatch.setattr(aiohttp, "ClientSession", fake_session)


@pytest.fixture
async def mock_podcast_source_rss_wav(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a podcast definition from the config."""

    filepath = Path(TEST_RSS_LOCATION) / "test_valid_wav.rss"

    with filepath.open() as file:
        rss = file.read()

    responses: dict[str, FakeResponseDef] = {
        "https://pytest.internal/rss/test_source": {"data": rss, "status": 200},
        "https://pytest.internal/images/test.jpg": {"data": b"jpg", "status": 200},
        "https://pytest.internal/audio/test.wav": {"data": TEST_WAV_FILE, "status": 200},
    }

    def fake_session(*args: Any, **kwargs: Any) -> FakeSession:
        return FakeSession(responses=responses)

    monkeypatch.setattr(aiohttp, "ClientSession", fake_session)


@pytest.fixture
async def mock_podcast_source_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a podcast definition from the config."""

    responses: dict[str, FakeResponseDef] = {}

    def fake_session(*args: Any, **kwargs: Any) -> FakeSession:
        return FakeSession(responses=responses)

    monkeypatch.setattr(aiohttp, "ClientSession", fake_session)
