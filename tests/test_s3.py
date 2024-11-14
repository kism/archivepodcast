"""App testing different config behaviours."""

import logging
import os

import pytest

ROOT_PATH = os.path.join(os.getcwd(), "archivepodcast")


@pytest.fixture
def mock_threads(monkeypatch):
    """Mock thread start to prevent threads from actually starting."""
    monkeypatch.setattr("threading.Thread.start", lambda _: None)


def test_config_valid(tmp_path, get_test_config, caplog, s3, mock_threads):
    """Test that the app can load config and the testing attribute is set."""
    config_file = "testing_true_valid_s3.toml"

    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]

    s3.create_bucket(Bucket=bucket_name)

    result = s3.list_buckets()
    assert len(result["Buckets"]) == 1

    from archivepodcast.ap_archiver import PodcastArchiver

    with caplog.at_level(logging.DEBUG):
        PodcastArchiver(
            app_settings=config["app"], podcast_list=config["podcast"], instance_path=tmp_path, root_path=ROOT_PATH
        )

    assert "Not using s3" not in caplog.text
    assert f"Authenticated s3, using bucket: {bucket_name}" in caplog.text
