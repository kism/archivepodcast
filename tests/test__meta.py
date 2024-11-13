"""Test versioning."""

import tomlkit

import archivepodcast


def test_version():
    """Test version variable."""
    with open("pyproject.toml", "rb") as f:
        pyproject_toml = tomlkit.load(f)
    assert pyproject_toml["project"]["version"] == archivepodcast.__version__
