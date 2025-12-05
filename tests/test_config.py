import pytest
from pydantic import HttpUrl

from archivepodcast.config import _LOG_INFO_MESSAGES, ArchivePodcastConfig

base_config = ArchivePodcastConfig()


def test_log_info_cdn_only_with_s3(caplog: pytest.LogCaptureFixture) -> None:
    """Test CDN-only setup (inet_path == cdn_domain) with S3 backend."""
    config = base_config.model_copy()
    config.app.storage_backend = "s3"
    config.app.inet_path = HttpUrl("https://cdn.example.com/")
    config.app.s3.cdn_domain = HttpUrl("https://cdn.example.com/")

    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=False)

    assert _LOG_INFO_MESSAGES["frontend_cdn"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["backend_s3"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_local"].strip() not in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_local_adhoc"].strip() not in caplog.text


def test_log_info_webserver_with_local(caplog: pytest.LogCaptureFixture) -> None:
    """Test webserver mode with local storage backend."""
    config = base_config.model_copy()
    config.app.storage_backend = "local"

    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=False)

    assert _LOG_INFO_MESSAGES["frontend_local"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["backend_local"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_cdn"].strip() not in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_local_adhoc"].strip() not in caplog.text


def test_log_info_webserver_with_s3(caplog: pytest.LogCaptureFixture) -> None:
    """Test webserver mode with S3 storage backend."""
    config = base_config.model_copy()
    config.app.storage_backend = "s3"
    config.app.inet_path = HttpUrl("http://localhost:5100/")
    config.app.s3.cdn_domain = HttpUrl("https://cdn.example.com/")

    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=False)

    assert _LOG_INFO_MESSAGES["frontend_local"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["backend_s3"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_cdn"].strip() not in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_local_adhoc"].strip() not in caplog.text


def test_log_info_adhoc_with_local(caplog: pytest.LogCaptureFixture) -> None:
    """Test adhoc mode with local storage backend."""
    config = base_config.model_copy()
    config.app.storage_backend = "local"

    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=True)

    assert _LOG_INFO_MESSAGES["frontend_local_adhoc"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["backend_local"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_cdn"].strip() not in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_local"].strip() not in caplog.text


def test_log_info_adhoc_with_s3(caplog: pytest.LogCaptureFixture) -> None:
    """Test adhoc mode with S3 storage backend (triggers mismatch warning)."""
    config = base_config.model_copy()
    config.app.storage_backend = "s3"
    config.app.inet_path = HttpUrl("http://localhost:5100/")
    config.app.s3.cdn_domain = HttpUrl("https://cdn.example.com/")

    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=True)

    assert _LOG_INFO_MESSAGES["frontend_local_adhoc"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["backend_s3"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["adhoc_s3_miss_match"].strip() in caplog.text
    assert str(config.app.inet_path) in caplog.text
    assert str(config.app.s3.cdn_domain) in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_cdn"].strip() not in caplog.text
    assert _LOG_INFO_MESSAGES["frontend_local"].strip() not in caplog.text


def test_log_info_adhoc_with_s3_matching_domains(caplog: pytest.LogCaptureFixture) -> None:
    """Test adhoc mode with S3 backend but matching domains (no warning expected)."""
    config = base_config.model_copy()
    config.app.storage_backend = "s3"
    config.app.inet_path = HttpUrl("https://cdn.example.com/")
    config.app.s3.cdn_domain = HttpUrl("https://cdn.example.com/")

    with caplog.at_level("INFO"):
        config.log_info(running_adhoc=True)

    # In adhoc mode with matching domains, it goes to CDN path first
    assert _LOG_INFO_MESSAGES["frontend_cdn"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["backend_s3"].strip() in caplog.text
    assert _LOG_INFO_MESSAGES["adhoc_s3_miss_match"].strip() not in caplog.text
