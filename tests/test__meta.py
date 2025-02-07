"""Test versioning and file generation."""

import os

import magic
import pytest
import tomlkit

import archivepodcast


def test_version_pyproject():
    """Verify version in pyproject.toml matches package version."""
    with open("pyproject.toml", "rb") as f:
        pyproject_toml = tomlkit.load(f)
    assert pyproject_toml["project"]["version"] == archivepodcast.__version__


def test_version_lock():
    """Verify version in uv.lock matches package version."""
    with open("uv.lock") as f:
        uv_lock = tomlkit.load(f)

    found_version = False
    for package in uv_lock["package"]:
        if package["name"] == "archivepodcast":
            assert package["version"] == archivepodcast.__version__
            found_version = True
            break

    assert found_version, "archivepodcast not found in uv.lock"


def test_wav_generation(tmp_path):
    """Test WAV file generation."""
    wav_path = os.path.join(tmp_path, "test.wav")
    with open(wav_path, "wb") as f:
        f.write(pytest.TEST_WAV_FILE)
    assert magic.from_file(wav_path, mime=True) == "audio/x-wav"
