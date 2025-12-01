import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from archivepodcast.archiver.podcast_archiver import PodcastArchiver
from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.downloader.downloader import PodcastDownloader
from tests.constants import FLASK_ROOT_PATH

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
        instance_path=tmp_path,
        root_path=FLASK_ROOT_PATH,
    )

    asyncio.run(apa._render_files())  # Needed in this case?

    return apa


@pytest.fixture
def no_render_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monkeypatch _render_files to prevent it from running."""

    async def dummy_render_files(self: PodcastArchiver) -> None:
        """Dummy render files function."""
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
        instance_path=tmp_path,
        root_path=FLASK_ROOT_PATH,
    )


# endregion

# region PodcastDownloader object


@pytest.fixture
def apd(
    apa: PodcastArchiver,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> PodcastDownloader:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid.json"
    config = get_test_config(config_file)

    web_root = apa.web_root

    return PodcastDownloader(app_config=config.app, s3=False, web_root=web_root)


@pytest.fixture
def apd_aws(
    apa_aws: PodcastArchiver,
    get_test_config: Callable[[str], ArchivePodcastConfig],
    caplog: pytest.LogCaptureFixture,
) -> PodcastDownloader:
    """Return a Podcast Archive Object with mocked AWS."""
    config_file = "testing_true_valid_s3.json"
    config = get_test_config(config_file)

    web_root = apa_aws.web_root

    return PodcastDownloader(app_config=config.app, s3=apa_aws.s3, web_root=web_root)
