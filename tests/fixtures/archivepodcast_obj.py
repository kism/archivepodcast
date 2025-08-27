import time

import pytest

from archivepodcast.ap_archiver import PodcastArchiver, PodcastDownloader


@pytest.fixture
def apa(tmp_path, get_test_config, caplog):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)

    apa = PodcastArchiver(
        app_config=config["app"],
        podcast_list=config["podcast"],
        instance_path=tmp_path,
        root_path=pytest.FLASK_ROOT_PATH,
    )

    while apa.health.core.currently_loading_config or apa.health.core.currently_rendering:
        time.sleep(0.05)

    return apa


@pytest.fixture
def no_render_files(monkeypatch):
    """Monkeypatch render_files to prevent it from running."""
    monkeypatch.setattr("archivepodcast.ap_archiver.PodcastArchiver.render_files", lambda _: None)


@pytest.fixture
def apa_aws(tmp_path, get_test_config, no_render_files, caplog, s3, mocked_aws):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    # Prevent weird threading issues

    apa_aws = PodcastArchiver(
        app_config=config["app"],
        podcast_list=config["podcast"],
        instance_path=tmp_path,
        root_path=pytest.FLASK_ROOT_PATH,
    )

    while apa_aws.health.core.currently_loading_config or apa_aws.health.core.currently_rendering:
        time.sleep(0.05)

    return apa_aws


# endregion

# region: PodcastDownloader object


@pytest.fixture
def apd(apa, get_test_config, caplog):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)

    web_root = apa.web_root

    return PodcastDownloader(app_config=config["app"], s3=None, web_root=web_root)


@pytest.fixture
def apd_aws(apa_aws, get_test_config, mocked_aws, caplog):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    web_root = apa_aws.web_root

    return PodcastDownloader(app_config=config["app"], s3=apa_aws.s3, web_root=web_root)
