"""Test versioning and file generation."""

from pathlib import Path

import magic
import tomlkit

from archivepodcast.version import __version__

from .constants import TEST_WAV_FILE


def test_version_pyproject() -> None:
    """Verify version in pyproject.toml matches package version."""
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as f:
        pyproject_toml = tomlkit.load(f)
    assert pyproject_toml.get("project", {}).get("version") == __version__, (
        "Version in pyproject.toml does not match package version."
    )


def test_version_lock() -> None:
    """Verify version in uv.lock matches package version."""
    lock_path = Path("uv.lock")
    with lock_path.open() as f:
        uv_lock = tomlkit.load(f)

    found_version = False
    for package in uv_lock.get("package", []):
        if package["name"] == "archivepodcast":
            assert package["version"] == __version__
            found_version = True
            break

    assert found_version, "archivepodcast not found in uv.lock"


def test_wav_generation(tmp_path: Path) -> None:
    """Test WAV file generation."""
    wav_path = tmp_path / "test.wav"
    wav_path.write_bytes(TEST_WAV_FILE)
    assert magic.from_file(str(wav_path), mime=True) == "audio/x-wav"
