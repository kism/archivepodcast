"""The conftest.py file serves as a means of providing fixtures for an entire directory.

Fixtures defined in a conftest.py can be used by any test in that package without needing to import them.
"""

import os
import shutil
from collections.abc import Callable

import boto3
import pytest
import tomlkit
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from moto import mock_aws

from archivepodcast.ap_archiver import PodcastArchiver

FLASK_ROOT_PATH = os.getcwd()
TEST_CONFIGS_LOCATION = os.path.join(os.getcwd(), "tests", "configs")
TEST_RSS_LOCATION = os.path.join(os.getcwd(), "tests", "rss")


def pytest_configure():
    """This is a magic function for adding things to pytest?"""
    pytest.TEST_CONFIGS_LOCATION = TEST_CONFIGS_LOCATION


@pytest.fixture
def app(tmp_path, get_test_config) -> Flask:
    """This fixture uses the default config within the flask app."""
    from archivepodcast import create_app

    return create_app(test_config=get_test_config("testing_true_valid.toml"), instance_path=tmp_path)


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """This returns a test client for the default app()."""
    return app.test_client()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    """TODO?????"""
    return app.test_cli_runner()


@pytest.fixture
def get_test_config() -> Callable:
    """Function returns a function, which is how it needs to be."""

    def _get_test_config(config_name: str) -> dict:
        """Load all the .toml configs into a single dict."""
        filepath = os.path.join(TEST_CONFIGS_LOCATION, config_name)

        with open(filepath) as file:
            return tomlkit.load(file)

    return _get_test_config


@pytest.fixture
def place_test_config() -> Callable:
    """Fixture that places a config in the tmp_path.

    Returns: a function to place a config in the tmp_path.
    """

    def _place_test_config(config_name: str, path: str) -> None:
        """Place config in tmp_path by name."""
        filepath = os.path.join(TEST_CONFIGS_LOCATION, config_name)

        shutil.copyfile(filepath, os.path.join(path, "config.toml"))

    return _place_test_config


@pytest.fixture  # We need to mock threads out since they won't have context
def mock_threads_none(monkeypatch):
    """Mock thread start to prevent threads from actually starting."""
    monkeypatch.setattr("threading.Thread.start", lambda _: None)


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "abc"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "xyz"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mocked_aws(aws_credentials):
    """Mock all AWS interactions, Requires you to create your own boto3 clients."""
    with mock_aws():
        yield


@pytest.fixture
def s3(aws_credentials):
    """Return a mocked S3 client."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def pa(tmp_path, get_test_config, caplog, mock_threads_none):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.toml"
    config = get_test_config(config_file)

    return PodcastArchiver(
        app_settings=config["app"], podcast_list=config["podcast"], instance_path=tmp_path, root_path=FLASK_ROOT_PATH
    )


@pytest.fixture
def pa_aws(tmp_path, get_test_config, monkeypatch, caplog, s3):
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.toml"
    config = get_test_config(config_file)

    bucket_name = config["app"]["s3"]["bucket"]
    s3.create_bucket(Bucket=bucket_name)

    # Prevent weird threading issues
    monkeypatch.setattr("archivepodcast.ap_archiver.PodcastArchiver.render_static", lambda _: None)

    from archivepodcast.ap_archiver import PodcastArchiver

    return PodcastArchiver(
        app_settings=config["app"],
        podcast_list=config["podcast"],
        instance_path=tmp_path,
        root_path=FLASK_ROOT_PATH,
    )


@pytest.fixture
def mock_get_podcast_source_rss(requests_mock) -> Callable:
    """Return a podcast definition from the config."""

    def _mock_get_podcast_source_rss(rss_name: str) -> str:
        """Return the rss file."""
        filepath = os.path.join(TEST_RSS_LOCATION, rss_name)

        with open(filepath) as file:
            rss = file.read()

        return requests_mock.get("https://pytest.internal/rss/test_source", text=rss)

    return _mock_get_podcast_source_rss


@pytest.fixture
def mock_podcast_source_images(requests_mock):
    """Requests mock for downloading an image."""
    requests_mock.get("https://pytest.internal/images/test.jpg", text="")


@pytest.fixture
def mock_podcast_source_mp3(requests_mock):
    """Requests mock for downloading an image."""
    requests_mock.get("https://pytest.internal/audio/test.mp3", text="")


@pytest.fixture
def mock_podcast_source_wav(requests_mock, tmp_path):
    """Requests mock for downloading an image."""
    from pydub import AudioSegment

    audio = AudioSegment.silent(duration=1000)

    tmp_wav_path = os.path.join(tmp_path, "test.wav")

    audio.export(tmp_wav_path, format="wav")

    with open(os.path.join(tmp_path, "test.wav"), "rb") as audio:
        audio_file = audio.read()

    requests_mock.get("https://pytest.internal/audio/test.wav", content=audio_file)

    os.remove(tmp_wav_path)
