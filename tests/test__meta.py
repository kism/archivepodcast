"""Test versioning."""

import os

import magic
import pytest
import tomlkit

import archivepodcast


def test_version():
    """Test version variable."""
    with open("pyproject.toml", "rb") as f:
        pyproject_toml = tomlkit.load(f)
    assert pyproject_toml["project"]["version"] == archivepodcast.__version__


def test_wav_generation(tmp_path):
    """Test WAV file generation."""
    wav_path = os.path.join(tmp_path, "test.wav")

    with open(wav_path, "wb") as f:
        f.write(pytest.TEST_WAV_FILE)

    assert magic.from_file(wav_path, mime=True) == "audio/x-wav"
