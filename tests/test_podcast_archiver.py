"""App testing different config behaviours."""

import logging
import os

import pytest

from archivepodcast.ap_archiver import PodcastArchiver

FLASK_ROOT_PATH = os.getcwd()


@pytest.fixture
def pa(tmp_path, get_test_config, caplog, mock_threads_none):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)

    return PodcastArchiver(
        app_settings=config["app"], podcast_list=config["podcast"], instance_path=tmp_path, root_path=FLASK_ROOT_PATH
    )


def test_no_about_page(pa, caplog):  # Move this to non aws tests
    """Test no about page."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        pa.make_about_page()

    assert "About page doesn't exist" in caplog.text
