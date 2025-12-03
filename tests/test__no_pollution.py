"""Tests to ensure that the flask app doesn't pollute test environments."""

import contextlib
import random
import shutil
import string
from collections.abc import Callable
from pathlib import Path

import pytest

from archivepodcast import create_app
from archivepodcast.config import ArchivePodcastConfig


def test_instance_path_check(get_test_config: Callable[[str], ArchivePodcastConfig], tmp_path: Path) -> None:
    """Ensure instance path is specified when using dictionary config."""

    with pytest.raises(ValueError, match="Flask TESTING mode requires instance_path to be a tmp_path"):
        create_app()


def test_config_validate_test_instance_path(get_test_config: Callable[[str], ArchivePodcastConfig]) -> None:
    """Verify that tmp_path is required in testing mode."""
    repo_instance_path = Path.cwd() / "instance"
    incorrect_instance_root = repo_instance_path / "_TEST"
    random_string = "".join(random.choice(string.ascii_uppercase) for _ in range(8))
    incorrect_instance_path = incorrect_instance_root / random_string

    with contextlib.suppress(FileNotFoundError, FileExistsError):
        repo_instance_path.mkdir(exist_ok=True)
        shutil.rmtree(incorrect_instance_root, ignore_errors=True)
        incorrect_instance_root.mkdir()
        incorrect_instance_path.mkdir()

    with pytest.raises(ValueError, match="Flask TESTING mode requires instance_path to be a tmp_path") as exc_info:
        create_app()

    assert isinstance(exc_info.type, type(ValueError))
    assert "Flask TESTING mode requires instance_path to be a tmp_path" in str(exc_info.getrepr())

    shutil.rmtree(incorrect_instance_root)
