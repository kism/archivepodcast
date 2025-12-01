import pytest


@pytest.fixture(autouse=True)
def patch_asyncio_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_sleep(_: float) -> None:
        pass

    monkeypatch.setattr("asyncio.sleep", fake_sleep)
