"""Test versioning."""

import os

import magic
import pytest
import tomlkit

import archivepodcast


def test_version_pyproject():
    """Test version variable."""
    with open("pyproject.toml", "rb") as f:
        pyproject_toml = tomlkit.load(f)
    assert (
        pyproject_toml["project"]["version"] == archivepodcast.__version__
    ), "Ensure pyproject.toml version matches __init__.py"


def test_version_lock():
    """Test version in lock file."""
    with open("uv.lock") as f:
        uv_lock = tomlkit.load(f)

    found_uv_lock_version = False

    for package in uv_lock["package"]:
        if package["name"] == "archivepodcast":
            assert (
                package["version"] == archivepodcast.__version__
            ), "uv.lock package version not in-sync, run: uv sync --upgrade"
            found_uv_lock_version = True

    assert found_uv_lock_version, "Ensure archivepodcast is in uv.lock"


def test_wav_generation(tmp_path):
    """Test WAV file generation."""
    wav_path = os.path.join(tmp_path, "test.wav")

    with open(wav_path, "wb") as f:
        f.write(pytest.TEST_WAV_FILE)

    assert magic.from_file(wav_path, mime=True) == "audio/x-wav"
