"""Test the application logger configuration."""

import logging

from flask import Flask

from archivepodcast import create_app


def test_config_invalid_log_level(tmp_path, get_test_config, caplog):
    """Verify application starts with invalid log level and logs warning."""
    caplog.set_level(logging.WARNING)
    app = create_app(get_test_config("logging_invalid_log_level.toml"), instance_path=tmp_path)
    assert isinstance(app, Flask)
    assert "Invalid logging level" in caplog.text
