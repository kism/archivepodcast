"""Test versioning and file generation."""

from pathlib import Path

import magic
import pytest
import tomlkit

import archivepodcast


def test_version_pyproject():
    """Verify version in pyproject.toml matches package version."""
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as f:
        pyproject_toml = tomlkit.load(f)
    assert pyproject_toml["project"]["version"] == archivepodcast.__version__


def test_version_lock():
    """Verify version in uv.lock matches package version."""
    lock_path = Path("uv.lock")
    with lock_path.open() as f:
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
    wav_path = tmp_path / "test.wav"
    wav_path.write_bytes(pytest.TEST_WAV_FILE)
    assert magic.from_file(str(wav_path), mime=True) == "audio/x-wav"
