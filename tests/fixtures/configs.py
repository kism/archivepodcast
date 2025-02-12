import shutil
from pathlib import Path

import pytest
import tomlkit


@pytest.fixture
def get_test_config():
    """Function returns a function, which is how it needs to be."""

    def _get_test_config(config_name):
        """Load all the .toml configs into a single dict."""
        filepath: Path = Path(pytest.TEST_CONFIGS_LOCATION) / config_name

        with filepath.open() as file:
            return tomlkit.load(file)

    return _get_test_config


@pytest.fixture
def place_test_config():
    """Fixture that places a config in the tmp_path.

    Returns: a function to place a config in the tmp_path.
    """

    def _place_test_config(config_name, path):
        """Place config in tmp_path by name."""
        filepath = Path(pytest.TEST_CONFIGS_LOCATION) / config_name

        shutil.copyfile(filepath, Path(path) / "config.toml")

    return _place_test_config
