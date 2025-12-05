import argparse
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from flask import Flask

from archivepodcast import __main__
from archivepodcast.utils import logger as ap_logger
from archivepodcast.utils.logger import LoggingConf

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
else:
    MockerFixture = object  # pragma: no cover


@pytest.fixture
def preserve_caplog_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture to preserve pytest's caplog handlers when setup_logger is called."""
    original_setup_logger = ap_logger.setup_logger

    def setup_logger_preserve_caplog(
        app: Flask | None,
        logging_conf: LoggingConf | None = None,
        in_logger: logging.Logger | None = None,
    ) -> None:
        root_logger = logging.getLogger()
        # Save pytest's caplog handlers
        caplog_handlers = list(root_logger.handlers)
        # Call original setup
        original_setup_logger(app, logging_conf, in_logger)
        # Re-add caplog handlers
        for handler in caplog_handlers:
            if handler not in root_logger.handlers:
                root_logger.addHandler(handler)

    monkeypatch.setattr(ap_logger, "setup_logger", setup_logger_preserve_caplog)


def test_archivepodcast_cli_from__main__(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    caplog: pytest.LogCaptureFixture,
    preserve_caplog_handlers: MockerFixture,
) -> None:
    """TEST: Run CLI from main."""
    os.environ["AP_SIMPLE_LOGGING"] = "true"
    place_test_config("testing_true_valid.json", tmp_path)

    mock_args = argparse.Namespace(
        instance_path=str(tmp_path),
        config=str(tmp_path / "config.json"),
    )
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    with caplog.at_level(logging.DEBUG):
        __main__.main()

    # We get to the intro
    assert "ArchivePodcast version" in caplog.text
    assert "Operating mode: Adhoc" in caplog.text


def test_archivepodcast_cli_from__main__no_provided_instance_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    caplog: pytest.LogCaptureFixture,
    preserve_caplog_handlers: None,
) -> None:
    """TEST: Run CLI from main."""
    os.environ["AP_SIMPLE_LOGGING"] = "true"
    place_test_config("testing_true_valid.json", tmp_path)

    monkeypatch.setattr(
        "archivepodcast.__main__.DEFAULT_INSTANCE_PATH",
        tmp_path,
    )  # Since this is set at import time, we have to patch it directly

    mock_args = argparse.Namespace(
        instance_path="",
    )
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    with caplog.at_level(logging.DEBUG):
        __main__.main()

    # We get to the intro
    assert "Using default instance path" in caplog.text
    assert f"{tmp_path}{os.sep}config.json" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        __main__.main()

    assert "not creating it for safety" not in caplog.text


def test_archivepodcast_cli_from__main__no_instance_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    place_test_config("testing_true_valid.json", tmp_path)

    monkeypatch.setattr("pathlib.Path.exists", lambda x: False)  # Avoid pytest from using the repo's instance path

    monkeypatch.setattr(
        "archivepodcast.constants.DEFAULT_INSTANCE_PATH",
        tmp_path,
    )  # Avoid pytest from using the repo's instance path

    mock_args = argparse.Namespace(
        instance_path="",
        config=str(tmp_path / "config.json"),
    )
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    with pytest.raises(FileNotFoundError):
        __main__.main()
