"""Test application configuration loading and validation."""

import logging
from pathlib import Path

import pytest

from archivepodcast import create_app
from archivepodcast.config import ConfigValidationError


def test_config_valid(tmp_path, get_test_config):
    """Verify app loads valid config and sets testing attribute correctly."""
    # TEST: Testing attribute set
    app = create_app(get_test_config("testing_true_valid.toml"), instance_path=tmp_path)
    assert app.testing, "Flask testing config item not being set correctly."

    # TEST: Testing attribute not set.
    # The config loaded sets testing to False, do not use this config for any other test.
    app = create_app(get_test_config("testing_false_valid.toml"), instance_path=tmp_path)
    assert not app.testing, "Flask testing config item not being set correctly."


def test_config_file_loading(place_test_config, tmp_path, caplog):
    """Test config file loading, use tmp_path."""
    place_test_config("testing_true_valid.toml", tmp_path)

    # TEST: Config file is created when no test_config is provided.
    caplog.set_level(logging.INFO)
    create_app(config_dict=None, instance_path=tmp_path)
    assert "Using this path as it's the first one that was found" in caplog.text


def test_config_file_creation(tmp_path, caplog):
    """TEST: that file is created when no config is provided.."""
    with caplog.at_level(logging.WARNING), pytest.raises(ConfigValidationError) as exc_info:
        create_app(config_dict=None, instance_path=tmp_path)

    assert Path(tmp_path / "config.toml").exists()
    assert "Podcast url is empty" in str(exc_info.value)
    assert "Podcast name_one_word is empty" in str(exc_info.value)
