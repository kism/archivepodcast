from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from requests_mock import Mocker

from tests.constants import TEST_RSS_LOCATION, TEST_WAV_FILE

if TYPE_CHECKING:
    from pytest_mock import MockerFixture  # pragma: no cover
    from requests_mock.adapter import _Matcher  # pragma: no cover
else:
    MockerFixture = object
    _Matcher = object


@pytest.fixture
def mock_get_podcast_source_rss(requests_mock: Mocker) -> Callable[[str], _Matcher]:
    """Return a podcast definition from the config."""

    def _mock_get_podcast_source_rss(rss_name: str) -> _Matcher:
        """Return the rss file."""
        filepath = Path(TEST_RSS_LOCATION) / rss_name

        with filepath.open() as file:
            rss = file.read()

        return requests_mock.get("https://pytest.internal/rss/test_source", text=rss)

    return _mock_get_podcast_source_rss


@pytest.fixture
def mock_podcast_source_images(requests_mock: Mocker) -> None:
    """Requests mock for downloading an image.

    Doesn't need to be real, but does need content since it will be removed if it is zero bytes.
    """
    requests_mock.get("https://pytest.internal/images/test.jpg", text="jpg")


@pytest.fixture
def mock_podcast_source_mp3(requests_mock: Mocker) -> None:
    """Requests mock for downloading an image.

    Doesn't need to be real, but does need content since it will be removed if it is zero bytes.
    """
    requests_mock.get("https://pytest.internal/audio/test.mp3", text="mp3")


@pytest.fixture
def mock_podcast_source_wav(requests_mock: Mocker, tmp_path: Path) -> None:
    """Requests mock for downloading a the test wav file.

    Unlike the fake mp3 files, this needs to be real since it will be converted.
    """
    requests_mock.get("https://pytest.internal/audio/test.wav", content=TEST_WAV_FILE)
