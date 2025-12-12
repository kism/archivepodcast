import json
from pathlib import Path

import pytest

from archivepodcast.config import AppS3Config, ArchivePodcastConfig

base_config = ArchivePodcastConfig()


def test_validate_api_url_empty_string() -> None:
    """Test api_url validator with empty string."""
    config = AppS3Config.model_validate({"api_url": ""})
    assert config.api_url is None


def test_validate_api_url_valid_url() -> None:
    """Test api_url validator with valid URL."""
    config = AppS3Config.model_validate({"api_url": "https://api.example.com"})
    assert str(config.api_url) == "https://api.example.com/"


def test_post_validate_missing_name_one_word() -> None:
    """Test post_validate raises error when name_one_word is empty."""
    config = base_config.model_copy()
    config.podcasts[0].name_one_word = ""

    with pytest.raises(ValueError, match="Please fill in the podcast details"):
        config.post_validate()


def test_write_config_new_file(tmp_path: Path) -> None:
    """Test writing config to a new file."""
    config_path = tmp_path / "config.json"
    config = base_config.model_copy()
    config.podcasts[0].name_one_word = "test"

    config.write_config(config_path)

    assert config_path.exists()


def test_write_config_existing_file_no_change(tmp_path: Path) -> None:
    """Test writing config when existing file matches."""
    config_path = tmp_path / "config.json"
    config = base_config.model_copy()
    config.podcasts[0].name_one_word = "test"

    # Write initial config
    config.write_config(config_path)

    # Write same config again
    config.write_config(config_path)

    assert config_path.exists()


def test_write_config_existing_file_with_change(tmp_path: Path) -> None:
    """Test writing config when existing file differs (creates backup)."""
    config_path = tmp_path / "config.json"
    config = base_config.model_copy()
    config.podcasts[0].name_one_word = "test"

    # Write initial config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w") as f:
        json.dump({"old": "data"}, f)

    # Write new config (should backup old)
    config.write_config(config_path)

    assert config_path.exists()
    backup_dir = config_path.parent / "config_backups"
    assert backup_dir.exists()


def test_force_load_config_file_missing(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Test loading config when file doesn't exist."""
    config_path = tmp_path / "nonexistent.json"

    with caplog.at_level("WARNING"):
        config = ArchivePodcastConfig.force_load_config_file(config_path)

    assert "does not exist" in caplog.text
    assert isinstance(config, ArchivePodcastConfig)


def test_force_load_config_file_existing(tmp_path: Path) -> None:
    """Test loading config from existing file."""
    config_path = tmp_path / "config.json"
    test_data = {
        "app": {"storage_backend": "s3"},
        "podcasts": [{"name_one_word": "test"}],
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w") as f:
        json.dump(test_data, f)

    config = ArchivePodcastConfig.force_load_config_file(config_path)

    assert config.app.storage_backend == "s3"
    assert config.podcasts[0].name_one_word == "test"
