import json
from pathlib import Path

from pydantic import HttpUrl

from archivepodcast.config import (
    AppConfig,
    AppS3Config,
    AppWebPageConfig,
    ArchivePodcastConfig,
    PodcastConfig,
)

# -- Generated content --------------------------------------------------------
# Generate the example configs from the pydantic models so the docs never drift.

_generated_dir = Path(__file__).parent / "_generated"
_generated_dir.mkdir(exist_ok=True)


def _write_example_config(name: str, config: ArchivePodcastConfig) -> None:
    (_generated_dir / name).write_text(
        json.dumps(json.loads(config.model_dump_json()), indent=2) + "\n", encoding="utf-8"
    )


def _example_config(app: AppConfig | None = None, podcasts: list[PodcastConfig] | None = None) -> ArchivePodcastConfig:
    kwargs = {"app": app} if app else {}
    if podcasts:
        kwargs["podcasts"] = podcasts
    return ArchivePodcastConfig(_env_file=None, **kwargs)  # ty: ignore[unknown-argument] # Don't let a local .env leak into the docs


_deploy_web_page = AppWebPageConfig(
    title="Podcast Archive",
    description="My Cool Podcast Archive",
    contact="email@example.com",
)
_deploy_podcasts = [
    PodcastConfig(
        url="https://feeds.megaphone.fm/replyall",
        new_name="Reply All [Archive]",
        name_one_word="replyall",
        contact_email="archivepodcast@localhost",
    )
]


def _deploy_s3(cdn_domain: str) -> AppS3Config:
    return AppS3Config(
        cdn_domain=HttpUrl(cdn_domain),
        api_url=HttpUrl("https://s3.us-east-1.example-s3-provider.com/"),
        bucket="my-bucket-name",
        region="us-east-1",
        access_key_id="my-access-key-id",
        secret_access_key="my-secret-access-key",
    )


_write_example_config(
    "example_config.json",
    _example_config(
        podcasts=[
            PodcastConfig(
                url="https://feeds.simplecast.com/CpvnpIaj",
                new_name="STown",
                name_one_word="stown",
            )
        ]
    ),
)

_write_example_config(
    "example_config_local.json",
    _example_config(
        app=AppConfig(inet_path=HttpUrl("https://mycooldomain.org/"), web_page=_deploy_web_page),
        podcasts=_deploy_podcasts,
    ),
)

_write_example_config(
    "example_config_s3_hybrid.json",
    _example_config(
        app=AppConfig(
            inet_path=HttpUrl("https://mycooldomain.org/"),
            storage_backend="s3",
            web_page=_deploy_web_page,
            s3=_deploy_s3("https://cdn.mycooldomain.org/"),
        ),
        podcasts=_deploy_podcasts,
    ),
)

_write_example_config(
    "example_config_s3_only.json",
    _example_config(
        app=AppConfig(
            inet_path=HttpUrl("https://mycooldomain.org/"),
            storage_backend="s3",
            web_page=_deploy_web_page,
            s3=_deploy_s3("https://mycooldomain.org/"),
        ),
        podcasts=_deploy_podcasts,
    ),
)

# -- Project information -----------------------------------------------------

project = "Archive Podcast"
copyright = "2025, Kieran Gee"
author = "Kieran Gee"


# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
]


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "sphinx_rtd_theme"
