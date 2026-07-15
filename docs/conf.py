import json
from pathlib import Path

from archivepodcast.config import ArchivePodcastConfig, PodcastConfig

# -- Generated content --------------------------------------------------------
# Generate the example config from the pydantic models so the docs never drift.

_example_config = ArchivePodcastConfig(
    _env_file=None,  # ty: ignore[unknown-argument] # Don't let a local .env leak into the docs
    podcasts=[
        PodcastConfig(
            url="https://feeds.simplecast.com/CpvnpIaj",
            new_name="STown",
            name_one_word="stown",
        )
    ],
)

_generated_dir = Path(__file__).parent / "_generated"
_generated_dir.mkdir(exist_ok=True)
(_generated_dir / "example_config.json").write_text(
    json.dumps(json.loads(_example_config.model_dump_json()), indent=2) + "\n", encoding="utf-8"
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
