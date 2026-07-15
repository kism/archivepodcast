"""Constants for the ArchivePodcast application."""

import os
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

OUR_TIMEZONE = datetime.now().astimezone().tzinfo or UTC
APP_DIRECTORY = Path(__file__).parent
DEFAULT_INSTANCE_PATH = Path.cwd() / "instance"

AP_SELF_TEST = os.getenv("AP_SELF_TEST", "false").lower() in {"true", "1", "yes"}
JSON_INDENT = 2
XML_ENCODING = "UTF-8"

PROGRAM_NAME = Path(__file__).parent.name.replace("_", "-").lower()  # Calculate this
PROGRAM_NAME_NICE = "ArchivePodcast"
PROGRAM_REPO_URL = "https://github.com/kism/archivepodcast"
try:
    PROGRAM_VERSION = version(PROGRAM_NAME)
except PackageNotFoundError:  # pragma: no cover
    PROGRAM_VERSION = "<unknown, please run uv sync>"


def _get_version_str() -> str:
    """Get a string representation of the version, including branch and commit hash."""
    repo_root = Path(__file__).parent.parent
    git_head_log = repo_root / ".git" / "logs" / "HEAD"
    git_head = repo_root / ".git" / "HEAD"
    last_commit = ""
    current_branch = ""

    if git_head_log.is_file():
        with git_head_log.open("r") as f:
            lines = f.readlines()
            if lines:  # pragma: no cover # This doesn't get hit in CI
                last_commit = lines[-1].strip().split(" ")[0][:7]  # Get the last commit hash, first 7 characters

    if git_head.is_file():
        with git_head.open("r") as f:
            current_branch = f.read().strip().split("/")[-1]

    return (
        f"{PROGRAM_NAME_NICE} "
        f"v{PROGRAM_VERSION}"
        f"{('-' + current_branch) if current_branch and (last_commit not in current_branch) else ''}"
        f"{('/' + last_commit + '') if last_commit else ''}"
    )


PROGRAM_NAME_WITH_VERSION = f"{PROGRAM_NAME_NICE} v{PROGRAM_VERSION}"
PROGRAM_NAME_WITH_FULL_VERSION: str = _get_version_str()
