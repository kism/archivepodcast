import os

import pytest


@pytest.fixture
def mock_get_podcast_source_rss(requests_mock):
    """Return a podcast definition from the config."""

    def _mock_get_podcast_source_rss(rss_name):
        """Return the rss file."""
        filepath = os.path.join(pytest.TEST_RSS_LOCATION, rss_name)

        with open(filepath) as file:
            rss = file.read()

        return requests_mock.get("https://pytest.internal/rss/test_source", text=rss)

    return _mock_get_podcast_source_rss


@pytest.fixture
def mock_podcast_source_images(requests_mock):
    """Requests mock for downloading an image.

    Doesn't need to be real, but does need content since it will be removed if it is zero bytes.
    """
    requests_mock.get("https://pytest.internal/images/test.jpg", text="jpg")


@pytest.fixture
def mock_podcast_source_mp3(requests_mock):
    """Requests mock for downloading an image.

    Doesn't need to be real, but does need content since it will be removed if it is zero bytes.
    """
    requests_mock.get("https://pytest.internal/audio/test.mp3", text="mp3")


@pytest.fixture
def mock_podcast_source_wav(requests_mock, tmp_path):
    """Requests mock for downloading a the test wav file.

    Unlike the fake mp3 files, this needs to be real since it will be converted.
    """
    requests_mock.get("https://pytest.internal/audio/test.wav", content=pytest.TEST_WAV_FILE)
