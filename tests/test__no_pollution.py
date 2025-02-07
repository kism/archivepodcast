"""Tests to ensure that the flask app doesn't pollute test environments."""

import contextlib
import os
import random
import shutil
import string

import pytest

from archivepodcast import create_app
from archivepodcast.config import ConfigValidationError


def test_instance_path_check(get_test_config):
    """Ensure instance path is specified when using dictionary config."""
    with pytest.raises(AttributeError):
        create_app(get_test_config("testing_false_valid.toml"))


def test_config_validate_test_instance_path(get_test_config):
    """Verify that tmp_path is required in testing mode."""
    repo_instance_path = os.path.join(os.getcwd(), "instance")
    incorrect_instance_root = os.path.join(repo_instance_path, "_TEST")
    random_string = "".join(random.choice(string.ascii_uppercase) for _ in range(8))
    incorrect_instance_path = os.path.join(incorrect_instance_root, random_string)

    with contextlib.suppress(FileNotFoundError, FileExistsError):
        os.mkdir(repo_instance_path)
        shutil.rmtree(incorrect_instance_root)
        os.mkdir(incorrect_instance_root)
        os.mkdir(incorrect_instance_path)

    with pytest.raises(ConfigValidationError) as exc_info:
        create_app(test_config=get_test_config("testing_true_valid.toml"), instance_path=incorrect_instance_path)

    assert isinstance(exc_info.type, type(ConfigValidationError))
    assert "['flask']['TESTING'] is True but instance_path is not a tmp_path" in str(exc_info.getrepr())

    shutil.rmtree(incorrect_instance_root)
