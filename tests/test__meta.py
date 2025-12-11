"""Test versioning and file generation."""

import tomllib
from pathlib import Path

import magic

from archivepodcast.version import __version__

from .constants import TEST_WAV_FILE


def test_version_pyproject() -> None:
    """Verify version in pyproject.toml matches package version."""
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as f:
        pyproject_toml = tomllib.load(f)
    assert pyproject_toml.get("project", {}).get("version") == __version__, (
        "Version in pyproject.toml does not match package version."
    )


def test_version_lock() -> None:
    """Verify version in uv.lock matches package version."""
    lock_path = Path("uv.lock")
    with lock_path.open("rb") as f:
        uv_lock = tomllib.load(f)

    package = next((pkg for pkg in uv_lock.get("package", []) if pkg["name"] == "archivepodcast"), None)
    assert package is not None, "archivepodcast not found in uv.lock"
    assert package["version"] == __version__


def test_wav_generation(tmp_path: Path) -> None:
    """Test WAV file generation."""
    wav_path = tmp_path / "test.wav"
    wav_path.write_bytes(TEST_WAV_FILE)
    assert magic.from_file(str(wav_path), mime=True) == "audio/x-wav"
