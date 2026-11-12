import pytest


@pytest.fixture(autouse=True)
def patch_delay_download(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_delay(_: int) -> None:
        pass

    monkeypatch.setattr("archivepodcast.downloader.asset_downloader.delay_download", fake_delay)
    monkeypatch.setattr("archivepodcast.downloader.downloader.delay_download", fake_delay)
