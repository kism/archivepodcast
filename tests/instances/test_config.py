"""Tests for the global config instance."""

import pytest

from archivepodcast.instances import config as config_instance


def test_get_ap_config_requires_path_on_first_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Getting the config before it is loaded, without a path, is an error."""
    monkeypatch.setattr(config_instance, "_conf_cache", None)

    with pytest.raises(ValueError, match="config_path must be provided"):
        config_instance.get_ap_config()
