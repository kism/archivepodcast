"""Instances for ArchivePodcast application."""

from pathlib import Path

from archivepodcast.config import ArchivePodcastConfig
from archivepodcast.utils.logger import get_logger

logger = get_logger(__name__)

_conf_cache: ArchivePodcastConfig | None = None


def get_ap_config(config_path: Path | None = None) -> ArchivePodcastConfig:
    """Get the global ArchivePodcastConfig instance."""
    global _conf_cache  # noqa: PLW0603
    if _conf_cache is None:
        from archivepodcast.config import ArchivePodcastConfig  # noqa: PLC0415

        if config_path is None:
            msg = "config_path must be provided the first time get_ap_config is called"
            raise ValueError(msg)

        _conf_cache = ArchivePodcastConfig().force_load_config_file(config_path)

    return _conf_cache
