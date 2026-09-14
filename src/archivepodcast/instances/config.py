"""Instances for ArchivePodcast application."""

from typing import TYPE_CHECKING

from archivepodcast.utils.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from archivepodcast.config import ArchivePodcastConfig

logger = get_logger(__name__)

_conf_cache: ArchivePodcastConfig | None = None


def get_ap_config(config_path: Path | None = None) -> ArchivePodcastConfig:
    """Get the global ArchivePodcastConfig instance."""
    global _conf_cache  # ruff: ignore[global-statement]
    if _conf_cache is None:
        from archivepodcast.config import ArchivePodcastConfig  # ruff: ignore[import-outside-top-level]

        if config_path is None:
            msg = "config_path must be provided the first time get_ap_config is called"
            raise ValueError(msg)

        _conf_cache = ArchivePodcastConfig().force_load_config_file(config_path)

    return _conf_cache
