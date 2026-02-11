"""Instances for ArchivePodcast application."""

from pathlib import Path

from pydantic import BaseModel

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


class S3ClientConfig(BaseModel):
    """Configuration for S3 client."""

    aws_secret_access_key: str
    aws_access_key_id: str
    region_name: str | None = None
    endpoint_url: str | None


def get_ap_config_s3_client() -> S3ClientConfig:
    """Get the S3 client from the global ArchivePodcastConfig instance."""
    ap_config = get_ap_config()

    return S3ClientConfig(
        aws_secret_access_key=ap_config.app.s3.secret_access_key,
        aws_access_key_id=ap_config.app.s3.access_key_id,
        region_name=ap_config.app.s3.region or None,
        endpoint_url=ap_config.app.s3.api_url.encoded_string() if ap_config.app.s3.api_url else None,
    )
