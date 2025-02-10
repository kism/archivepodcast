import os
import shutil
import threading
import time

import boto3
import pytest
import tomlkit
from moto import mock_aws

from archivepodcast.ap_archiver import PodcastArchiver, PodcastDownloader


@pytest.fixture
def get_test_config():
    """Function returns a function, which is how it needs to be."""

    def _get_test_config(config_name):
        """Load all the .toml configs into a single dict."""
        filepath = os.path.join(pytest.TEST_CONFIGS_LOCATION, config_name)

        with open(filepath) as file:
            return tomlkit.load(file)

    return _get_test_config


@pytest.fixture
def place_test_config():
    """Fixture that places a config in the tmp_path.

    Returns: a function to place a config in the tmp_path.
    """

    def _place_test_config(config_name, path):
        """Place config in tmp_path by name."""
        filepath = os.path.join(pytest.TEST_CONFIGS_LOCATION, config_name)

        shutil.copyfile(filepath, os.path.join(path, "config.toml"))

    return _place_test_config
