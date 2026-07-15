from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from archivepodcast import create_app
from tests.constants import DUMMY_RSS_STR

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from fastapi import FastAPI
    from pytest_mock import MockerFixture

    from archivepodcast.config import ArchivePodcastConfig
else:
    MockerFixture = object


@pytest.fixture
def app(tmp_path: Path, get_test_config: Callable[[str], ArchivePodcastConfig]) -> FastAPI:
    """This fixture uses the default config within the app."""

    # Create a dummy RSS file since this app instance is not live and requires an existing rss feed.
    (tmp_path / "web" / "rss").mkdir(parents=True)
    with (tmp_path / "web" / "rss" / "test").open("w") as file:
        file.write(DUMMY_RSS_STR)

    return create_app(instance_path_override=str(tmp_path))


@pytest.fixture
def app_live(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    no_threading_start: MockerFixture,
    mock_podcast_source_rss_valid: MockerFixture,
) -> FastAPI:
    """This fixture uses the default config within the app."""
    get_test_config("testing_true_valid_live.json")

    return create_app(instance_path_override=str(tmp_path))


@pytest.fixture
def app_live_s3(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    no_threading_start: MockerFixture,
    mock_podcast_source_rss_valid: MockerFixture,
) -> FastAPI:
    """This fixture uses the default config within the app."""

    return create_app(instance_path_override=str(tmp_path))


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:
    """This returns a test client for the default app()."""
    # The context manager runs the lifespan; follow_redirects=False so 307 redirect assertions see the redirect itself.
    with TestClient(app, follow_redirects=False) as client:
        yield client


@pytest.fixture
def client_live(app_live: FastAPI) -> Generator[TestClient]:
    """This returns a test client for the default app()."""
    with TestClient(app_live, follow_redirects=False) as client:
        yield client


@pytest.fixture
def client_live_s3(app_live_s3: FastAPI) -> Generator[TestClient]:
    """This returns a test client for the default app()."""
    with TestClient(app_live_s3, follow_redirects=False) as client:
        yield client
