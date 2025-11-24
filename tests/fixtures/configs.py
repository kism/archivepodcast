import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

import archivepodcast
from archivepodcast.config import ArchivePodcastConfig
from tests.constants import TEST_CONFIGS_LOCATION


@pytest.fixture
def get_test_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[str], ArchivePodcastConfig]:
    """Function returns a function, which is how it needs to be."""

    def _get_test_config(config_name: str = "testing_true_valid.json") -> ArchivePodcastConfig:
        """Load all the .json configs into a single dict."""
        filepath: Path = TEST_CONFIGS_LOCATION / config_name

        config = ArchivePodcastConfig().force_load_config_file(filepath)

        monkeypatch.setattr(archivepodcast.instances, "_conf_cache", config)

        return config

    _get_test_config()  # Ensure that it's always patched.

    return _get_test_config


@pytest.fixture
def place_test_config() -> Callable[[str, Path], None]:
    """Fixture that places a config in the tmp_path.

    Returns: a function to place a config in the tmp_path.
    """

    def _place_test_config(config_name: str, path: Path) -> None:
        """Place config in tmp_path by name."""
        filepath = TEST_CONFIGS_LOCATION / config_name

        shutil.copyfile(filepath, Path(path) / "config.json")

    return _place_test_config
