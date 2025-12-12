from pathlib import Path

import pytest

from archivepodcast.instances.path_helper import get_app_paths


def test_get_app_paths_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that getting app paths without setting raises RuntimeError."""

    monkeypatch.setattr(
        "archivepodcast.instances.path_helper._app_paths",
        None,
    )

    msg = "Application paths helper instance has not been set."
    with pytest.raises(RuntimeError, match=msg):
        get_app_paths()


def test_get_app_paths_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that app paths can be set and retrieved."""

    monkeypatch.setattr(
        "archivepodcast.instances.path_helper._app_paths",
        None,
    )

    get_app_paths(root_path=tmp_path, instance_path=tmp_path / "instance")
