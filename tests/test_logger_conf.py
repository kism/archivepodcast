"""Logger unit tests."""

import logging
import random
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from archivepodcast.utils.logger import (
    TRACE_LEVEL_NUM,
    LoggingConf,
)
from tests.helpers import assert_no_warnings_in_caplog

if TYPE_CHECKING:
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
