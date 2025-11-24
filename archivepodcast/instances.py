"""Instances for ArchivePodcast application."""

from pathlib import Path

from .config import ArchivePodcastConfig

_conf_cache: ArchivePodcastConfig | None = None


def get_ap_config(config_path: Path | None = None) -> ArchivePodcastConfig:
    """Get the global ArchivePodcastConfig instance."""
    global _conf_cache  # noqa: PLW0603
    if _conf_cache is None:
        from .ap_constants import SETTINGS_FILE  # noqa: PLC0415
        from .config import ArchivePodcastConfig  # noqa: PLC0415

        if config_path is not None:
            _conf_cache = ArchivePodcastConfig().force_load_config_file(config_path)
        else:
            _conf_cache = ArchivePodcastConfig().force_load_config_file(SETTINGS_FILE)
    return _conf_cache
