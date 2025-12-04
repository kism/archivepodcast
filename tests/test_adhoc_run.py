import argparse
import logging
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from archivepodcast import __main__


def test_archivepodcast_cli_from__main__(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TEST: Run CLI from main."""
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
    assert "starting in adhoc mode" in caplog.text


def test_archivepodcast_cli_from__main__no_provided_instance_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """TEST: Run CLI from main."""
    place_test_config("testing_true_valid.json", tmp_path)

    monkeypatch.setattr(
        "archivepodcast.__main__.DEFAULT_INSTANCE_PATH",
        tmp_path,
    )  # Since this is set at import time, we have to patch it directly

    mock_args = argparse.Namespace(
        instance_path="",
    )
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    with caplog.at_level(logging.INFO):
        __main__.main()

    # We get to the intro
    assert "Instance path not provided, using default" in caplog.text
    assert f"{tmp_path}{os.sep}config.json" in caplog.text

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
