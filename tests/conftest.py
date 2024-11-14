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

TEST_CONFIGS_LOCATION = os.path.join(os.getcwd(), "tests", "configs")


def pytest_configure():
    """This is a magic function for adding things to pytest?"""
    pytest.TEST_CONFIGS_LOCATION = TEST_CONFIGS_LOCATION


@pytest.fixture
def app(tmp_path, get_test_config, mocked_aws) -> Flask:
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


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3(aws_credentials):
    """Return a mocked S3 client."""
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture
def mocked_aws(aws_credentials):
    """Mock all AWS interactions, Requires you to create your own boto3 clients."""
    with mock_aws():
        yield
