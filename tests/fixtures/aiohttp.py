from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, TypedDict

import aiohttp
import pytest

from tests.constants import TEST_RSS_LOCATION, TEST_WAV_FILE

if TYPE_CHECKING:
    from aiohttp.pytest_plugin import AiohttpServer
    from pytest_mock import MockerFixture  # pragma: no cover
else:
    MockerFixture = object
    AiohttpServer = object


class FakeResponseDef(TypedDict):
    status: int
    data: bytes | str


class FakeContent:
    def __init__(self, data: bytes):
        self._data = data
        self._position = 0

    async def read(self, size: int = -1) -> bytes:
        if size == -1:
            result = self._data[self._position :]
            self._position = len(self._data)
            return result
        result = self._data[self._position : self._position + size]
        self._position += size
        return result


class FakeResponse:
    def __init__(self, data: str | bytes, status: int = 200):
        if isinstance(data, str):
            self._data = data.encode()
        else:
            self._data = data
        self.status = status
        self.content = FakeContent(self._data)

    def raise_for_status(self) -> None:
        if self.status >= HTTPStatus.BAD_REQUEST:
            raise aiohttp.ClientResponseError(
                request_info=None,  # type: ignore[arg-type]
                history=(),
                status=self.status,
            )

    async def json(self) -> Any:
        return self._data

    async def text(self) -> str:
        return self._data.decode()

    async def read(self) -> bytes:
        return self._data

    async def raw_headers(self) -> bytes:
        return b""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponseDef]):
        self.responses = responses

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        response_def = self.responses.get(url)
        if response_def is None:
            return FakeResponse(data=b"", status=404)

        return FakeResponse(data=response_def["data"], status=response_def["status"])

    async def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        response_def = self.responses.get(url)
        if response_def is None:
            return FakeResponse(data=b"", status=404)

        return FakeResponse(data=response_def["data"], status=response_def["status"])

    async def send(self, *args: object, **kwargs: object) -> FakeResponse:
        return FakeResponse(data=b"", status=404)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def close(self) -> None:
        pass


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
