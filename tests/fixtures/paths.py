from pathlib import Path

import pytest

from archivepodcast.utils.paths_helper import AppPathsHelper
from tests.constants import FLASK_ROOT_PATH


@pytest.fixture(autouse=True)
def mock_app_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Mock application paths for testing."""
    app_paths_mock = AppPathsHelper(root_path=FLASK_ROOT_PATH, instance_path=tmp_path)

    monkeypatch.setattr("archivepodcast.instances.path_helper._app_paths", app_paths_mock)
