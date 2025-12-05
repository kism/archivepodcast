import pytest

from archivepodcast.config import ArchivePodcastConfig

base_config = ArchivePodcastConfig()


def test_config_operating_mode_messages(caplog: pytest.LogCaptureFixture) -> None:
    """Test operating mode log messages."""
    # Test webserver with local storage
    config = base_config.model_copy()
    config.app.storage_backend = "local"
    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=False)
    assert "Frontend: Served via this webserver." in caplog.text
    assert "Storage backend: Local filesystem" in caplog.text
    assert "S3" not in caplog.text

    caplog.clear()

    # Test webserver with S3 storage
    config = base_config.model_copy()
    config.app.storage_backend = "s3"
    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=False)
    assert "Frontend: Served via this webserver." in caplog.text
    assert "Storage backend: S3" in caplog.text
    assert "Local" not in caplog.text

    caplog.clear()

    # Test adhoc with local storage
    config = base_config.model_copy()
    config.app.storage_backend = "local"
    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=True)
    assert "Frontend: Not served" in caplog.text
    assert "Storage backend: Local filesystem" in caplog.text
