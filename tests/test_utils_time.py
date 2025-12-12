import logging

import pytest

from archivepodcast.utils.time import _WARN_THRESHOLD, warn_if_too_long


def test_warn_if_too_long_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_if_too_long("test", _WARN_THRESHOLD - 1)
        warn_if_too_long("test", _WARN_THRESHOLD - 1, large_file=True)

    assert "took longer than expected" not in caplog.text


def test_warn_if_too_long_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_if_too_long("test", _WARN_THRESHOLD + 1)

    assert "test took longer than expected: 6s" in caplog.text

    caplog.clear()

    with caplog.at_level(logging.WARNING):
        warn_if_too_long("test", _WARN_THRESHOLD * 11, large_file=True)

    assert "test took longer than expected" in caplog.text
