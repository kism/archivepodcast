"""Logger unit tests."""

import logging
import os
from collections.abc import Generator

import pytest
import pytest_mock
from flask import Flask

import archivepodcast.logger


@pytest.fixture
def logger() -> Generator:
    """Logger to use in unit tests, including cleanup."""
    logger = logging.getLogger("TEST_LOGGER")

    assert len(logger.handlers) == 0  # Check the logger has no handlers

    yield logger

    # Reset the test object since it will persist.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

@pytest.mark.filterwarnings("ignore:.*:pytest.PytestUnhandledThreadExceptionWarning")
def test_logging_permissions_error(logger, tmp_path, mocker: pytest_mock.plugin.MockerFixture):
    """Test logging, mock a permission error."""
    from archivepodcast.logger import _add_file_handler

    mock_open_func = mocker.mock_open(read_data="")
    mock_open_func.side_effect = PermissionError("Permission denied")

    mocker.patch("builtins.open", mock_open_func)

    # TEST: That a permissions error is raised when open() results in a permissions error.
    with pytest.raises(PermissionError):
        _add_file_handler(logger, str(tmp_path))


def test_config_logging_to_dir(logger, tmp_path):
    """TEST: Correct exception is caught when you try log to a folder."""
    from archivepodcast.logger import _add_file_handler

    with pytest.raises(IsADirectoryError):
        _add_file_handler(logger, tmp_path)


def test_handler_console_added(logger, app: Flask):
    """Test logging console handler."""
    logging_conf = {"path": "", "level": "INFO"}  # Test only console handler

    # TEST: Only one handler (console), should exist when no logging path provided
    archivepodcast.logger.setup_logger(app, logging_conf, logger)
    assert len(logger.handlers) == 1

    # TEST: If a console handler exists, another one shouldn't be created
    archivepodcast.logger.setup_logger(app, logging_conf, logger)
    assert len(logger.handlers) == 1


def test_handler_file_added(logger, tmp_path, app: Flask):
    """Test logging file handler."""
    logging_conf = {"path": os.path.join(tmp_path, "test.log"), "level": "INFO"}  # Test file handler

    # TEST: Two handlers when logging to file expected
    archivepodcast.logger.setup_logger(app, logging_conf, logger)
    assert len(logger.handlers) == 2  # noqa: PLR2004 A console and a file handler are expected

    # TEST: Two handlers when logging to file expected, another one shouldn't be created
    archivepodcast.logger.setup_logger(app, logging_conf, logger)
    assert len(logger.handlers) == 2  # noqa: PLR2004 A console and a file handler are expected


@pytest.mark.parametrize(
    ("log_level_in", "log_level_expected"),
    [
        (50, 50),
        ("INFO", 20),
        ("WARNING", 30),
        ("INVALID", 20),
    ],
)
def test_set_log_level(log_level_in: str | int, log_level_expected: int, logger):
    """Test if _set_log_level results in correct log_level."""
    from archivepodcast.logger import _set_log_level

    # TEST: Logger ends up with correct values
    _set_log_level(logger, log_level_in)
    assert logger.getEffectiveLevel() == log_level_expected


def test_colour():
    """Test colour messages."""
    from archivepodcast.logger import ColorFormatter

    formatter = ColorFormatter()

    class TestRecord(logging.LogRecord):
        def __init__(self, levelno, msg) -> None:
            self.levelno = levelno
            self.msg = msg
            self.name = "Test_Logger"
            self.args = ()
            self.exc_info = None
            self.exc_text = None
            self.stack_info = None
            self.levelname = logging.getLevelName(levelno)

    log_records = [
        TestRecord(levelno=10, msg="Test message str"),
        TestRecord(levelno=10, msg=None),
        TestRecord(levelno=10, msg=["Test", "message", "list"]),
        TestRecord(levelno=10, msg=("Test", "message", "tuple")),
    ]

    for i in log_records:
        assert formatter.format(i)


def test_trace_log_level():
    """Test trace log level."""
    from archivepodcast.logger import TRACE_LEVEL_NUM, CustomLogger

    custom_logger = CustomLogger("TEST_LOGGER")
    custom_logger.trace("Test trace message")

    assert logging.getLevelName(TRACE_LEVEL_NUM) == "TRACE"
    assert logging._nameToLevel["TRACE"] == TRACE_LEVEL_NUM
