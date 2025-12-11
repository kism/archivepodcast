from collections.abc import Callable
from pathlib import Path

import pytest

from archivepodcast.lambda_handler import handler


def test_run_lambda(
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    tmp_path: Path,
) -> None:
    """Test the lambda handler function with a mock event and context."""

    _ro_test_instance_path = tmp_path / "instance_ro"
    _test_instance_path = tmp_path / "instance"

    _ro_test_instance_path.mkdir()
    _test_instance_path.mkdir()

    place_test_config("testing_true_valid.json", _ro_test_instance_path)

    monkeypatch.setattr("archivepodcast.lambda_handler.LOCAL_RO_INSTANCE_PATH", _ro_test_instance_path)
    monkeypatch.setattr("archivepodcast.lambda_handler.INSTANCE_PATH", _test_instance_path)

    handler(None, None)  # type: ignore[arg-type]


def test_run_lambda_no_ro_instance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test the lambda handler function when the RO instance path does not exist."""

    monkeypatch.setattr("archivepodcast.lambda_handler.LOCAL_RO_INSTANCE_PATH", tmp_path / "nonexistent")
    monkeypatch.setattr("archivepodcast.lambda_handler.INSTANCE_PATH", tmp_path / "instance")

    with pytest.raises(FileNotFoundError, match="Instance path does not exist"):
        handler(None, None)  # type: ignore[arg-type]


def test_run_lambda_no_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test the lambda handler function when the config.json file is missing."""

    _ro_test_instance_path = tmp_path / "instance_ro"
    _ro_test_instance_path.mkdir()

    monkeypatch.setattr("archivepodcast.lambda_handler.LOCAL_RO_INSTANCE_PATH", _ro_test_instance_path)
    monkeypatch.setattr("archivepodcast.lambda_handler.INSTANCE_PATH", tmp_path / "instance")

    with pytest.raises(FileNotFoundError, match=r"Instance config.json not found"):
        handler(None, None)  # type: ignore[arg-type]
