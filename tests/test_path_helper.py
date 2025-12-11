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
