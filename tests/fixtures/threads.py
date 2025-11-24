import threading
from collections.abc import Generator
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def error_on_raise_in_thread(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """Replaces Thread with a a wrapper to record any exceptions and re-raise them after test execution.

    In case multiple threads raise exceptions only one will be raised.
    """
    last_exception = None

    class ThreadWrapper(threading.Thread):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)

        def run(self) -> None:
            """Mocked thread.run() method to capture exceptions."""
            try:
                super().run()
            except BaseException as e:
                nonlocal last_exception
                last_exception = e

    monkeypatch.setattr("threading.Thread", ThreadWrapper)
    yield
    if last_exception:
        raise last_exception
