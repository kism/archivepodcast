"""Startup self-check that Git LFS assets were actually fetched, not left as pointer stubs."""

import os
from typing import TYPE_CHECKING

from archivepodcast.utils.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

# https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md#the-pointer
_LFS_POINTER_MAGIC = b"version https://git-lfs.github.com/spec/v1"
_PEEK_BYTES = 200

SKIP_LFS_CHECK = (os.environ.get("CI_SKIP_LFS_CHECK") or "").lower() == "true"


def _is_lfs_pointer(path: Path) -> bool:
    """Check whether a file is an unresolved Git LFS pointer stub rather than real content."""
    with path.open("rb") as f:
        return f.read(_PEEK_BYTES).startswith(_LFS_POINTER_MAGIC)


def check_lfs_objects(static_directory: Path) -> None:
    """Raise if any file under static_directory is an unresolved Git LFS pointer.

    Checking out without Git LFS support (e.g. actions/checkout without `lfs: true`)
    leaves LFS-tracked files as small text pointer stubs instead of real content.
    """
    if SKIP_LFS_CHECK:
        return

    broken = [item for item in static_directory.rglob("*") if item.is_file() and _is_lfs_pointer(item)]

    if not broken:
        return

    for item in broken:
        logger.error("Git LFS pointer not resolved to real content: %s", item)

    msg = (
        f"{len(broken)} static file(s) are unresolved Git LFS pointers, not real content. "
        "Check out the repo with Git LFS enabled (e.g. 'git lfs pull', or 'lfs: true' on actions/checkout)."
    )
    raise RuntimeError(msg)
