from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

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


def test_run_lambda_copies_instance_folder(
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    tmp_path: Path,
) -> None:
    """Test that the lambda handler copies the RO instance folder to the writable location."""

    _ro_test_instance_path = tmp_path / "instance_ro"
    _test_instance_path = tmp_path / "instance"

    _ro_test_instance_path.mkdir()
    _test_instance_path.mkdir()

    # Create additional files to verify they get copied
    (place_test_config("testing_true_valid.json", _ro_test_instance_path))
    test_file = _ro_test_instance_path / "test_file.txt"
    test_file.write_text("test content")

    monkeypatch.setattr("archivepodcast.lambda_handler.LOCAL_RO_INSTANCE_PATH", _ro_test_instance_path)
    monkeypatch.setattr("archivepodcast.lambda_handler.INSTANCE_PATH", _test_instance_path)

    handler(None, None)  # type: ignore[arg-type]

    # Verify files were copied
    assert (_test_instance_path / "config.json").exists()
    assert (_test_instance_path / "test_file.txt").exists()
    assert (_test_instance_path / "test_file.txt").read_text() == "test content"


def test_run_lambda_calls_run_ap_adhoc(
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    tmp_path: Path,
) -> None:
    """Test that the lambda handler calls run_ap_adhoc with the correct instance path."""

    _ro_test_instance_path = tmp_path / "instance_ro"
    _test_instance_path = tmp_path / "instance"

    _ro_test_instance_path.mkdir()
    _test_instance_path.mkdir()

    place_test_config("testing_true_valid.json", _ro_test_instance_path)

    monkeypatch.setattr("archivepodcast.lambda_handler.LOCAL_RO_INSTANCE_PATH", _ro_test_instance_path)
    monkeypatch.setattr("archivepodcast.lambda_handler.INSTANCE_PATH", _test_instance_path)

    # Mock run_ap_adhoc to verify it's called correctly
    mock_run_ap_adhoc = Mock()
    monkeypatch.setattr("archivepodcast.lambda_handler.run_ap_adhoc", mock_run_ap_adhoc)

    handler(None, None)  # type: ignore[arg-type]

    # Verify run_ap_adhoc was called with the correct path
    mock_run_ap_adhoc.assert_called_once_with(instance_path=_test_instance_path)


def test_run_lambda_existing_instance_overwrites(
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    tmp_path: Path,
) -> None:
    """Test that handler overwrites existing instance folder content."""

    _ro_test_instance_path = tmp_path / "instance_ro"
    _test_instance_path = tmp_path / "instance"

    _ro_test_instance_path.mkdir()
    _test_instance_path.mkdir()

    place_test_config("testing_true_valid.json", _ro_test_instance_path)

    # Create an old file in the instance path
    old_file = _test_instance_path / "old_file.txt"
    old_file.write_text("old content")

    # Create a new file in the RO path
    new_file = _ro_test_instance_path / "new_file.txt"
    new_file.write_text("new content")

    monkeypatch.setattr("archivepodcast.lambda_handler.LOCAL_RO_INSTANCE_PATH", _ro_test_instance_path)
    monkeypatch.setattr("archivepodcast.lambda_handler.INSTANCE_PATH", _test_instance_path)

    handler(None, None)  # type: ignore[arg-type]

    # Verify new file was copied
    assert (_test_instance_path / "new_file.txt").exists()
    assert (_test_instance_path / "new_file.txt").read_text() == "new content"

    # Old file should still exist (dirs_exist_ok=True doesn't delete existing files)
    assert old_file.exists()


def test_run_lambda_logs_event(
    monkeypatch: pytest.MonkeyPatch,
    place_test_config: Callable[[str, Path], None],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the lambda handler logs the incoming event."""

    _ro_test_instance_path = tmp_path / "instance_ro"
    _test_instance_path = tmp_path / "instance"

    _ro_test_instance_path.mkdir()
    _test_instance_path.mkdir()

    place_test_config("testing_true_valid.json", _ro_test_instance_path)

    monkeypatch.setattr("archivepodcast.lambda_handler.LOCAL_RO_INSTANCE_PATH", _ro_test_instance_path)
    monkeypatch.setattr("archivepodcast.lambda_handler.INSTANCE_PATH", _test_instance_path)

    mock_event = {"test": "event", "data": "value"}

    with caplog.at_level("INFO"):
        handler(mock_event, None)  # type: ignore[arg-type]

    # Verify event was logged
    assert any("Event invoked with event:" in record.message for record in caplog.records)
