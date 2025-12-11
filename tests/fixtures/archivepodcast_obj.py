import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.downloader.downloader import PodcastsDownloader
from tests.models.aiohttp import FakeSession

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.fixtures.aws import AWSAioSessionMock
else:
    MockerFixture = object
    AWSAioSessionMock = object


@pytest.fixture
def apa(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> PodcastArchiver:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)

    apa = PodcastArchiver(
        app_config=config.app,
        podcast_list=config.podcasts,
    )

    asyncio.run(apa.renderer.render_files())  # Needed in this case?

    return apa


@pytest.fixture
def no_render_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch _render_files to prevent it from running."""

    async def dummy_render_files(self: PodcastArchiver) -> None:
        """No-op replacement for render_files."""
        return

    monkeypatch.setattr("archivepodcast.archiver.PodcastArchiver._render_files", dummy_render_files)


@pytest.fixture
def apa_aws(
    tmp_path: Path,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    mock_get_session: AWSAioSessionMock,
    caplog: pytest.LogCaptureFixture,
) -> PodcastArchiver:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)

    return PodcastArchiver(
        app_config=config.app,
        podcast_list=config.podcasts,
    )


# endregion

# region PodcastsDownloader object


@pytest.fixture
def apd(
    apa: PodcastArchiver,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> PodcastsDownloader:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)
    podcast = apa.podcast_list[0]
    aiohttp_session = FakeSession(responses={})

    return PodcastsDownloader(app_config=config.app, s3=False, podcast=podcast, aiohttp_session=aiohttp_session)  # type: ignore[arg-type]


@pytest.fixture
def apd_aws(
    apa_aws: PodcastArchiver,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> PodcastsDownloader:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)
    podcast = apa_aws.podcast_list[0]
    aiohttp_session = FakeSession(responses={})

    return PodcastsDownloader(app_config=config.app, s3=apa_aws.s3, podcast=podcast, aiohttp_session=aiohttp_session)  # type: ignore[arg-type]
