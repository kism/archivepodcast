"""Logger unit tests."""

import logging
from typing import TYPE_CHECKING

from archivepodcast.utils.logger import LoggingConf

if TYPE_CHECKING:
    import pytest
    from pytest_mock import MockerFixture
else:
    MockerFixture = object


def test_invalid_log_level(caplog: pytest.LogCaptureFixture) -> None:
    """Test setting an invalid log level."""
    # Invalid string level
    with caplog.at_level(logging.WARNING):
        conf = LoggingConf(level="INVALID_LEVEL", path=None)

    assert "Invalid logging level" in caplog.text
    assert conf.level == "INFO"
    caplog.clear()

    # Invalid int level high
    with caplog.at_level(logging.WARNING):
        conf = LoggingConf(level=10000, path=None)

    assert "Invalid logging level" in caplog.text
    assert conf.level == "INFO"
    caplog.clear()

    # Invalid int level low
    with caplog.at_level(logging.WARNING):
        conf = LoggingConf(level=-10000, path=None)

    assert "Invalid logging level" in caplog.text
    assert conf.level == "INFO"
    caplog.clear()


def test_set_path_validator() -> None:
    """Test the path validator."""

    # None path
    conf = LoggingConf(level="INFO", path=None)

    conf.set_path(None)
    assert conf.path is None

    conf.set_path("")
    assert conf.path is None
