from typing import TYPE_CHECKING

import pytest

from archivepodcast.utils.lfs_check import check_lfs_objects

if TYPE_CHECKING:
    from pathlib import Path


def test_check_lfs_objects_passes_for_real_content(tmp_path: Path) -> None:
    """Test that ordinary files don't trip the check."""
    (tmp_path / "main.css").write_text("body { color: red; }")
    (tmp_path / "favicon.ico").write_bytes(b"\x00\x00\x01\x00 not actually an ico but not a pointer either")

    check_lfs_objects(tmp_path)  # Should not raise


def test_check_lfs_objects_raises_for_unresolved_pointer(tmp_path: Path) -> None:
    """Test that an unresolved Git LFS pointer stub is detected."""
    (tmp_path / "main.css").write_text("body { color: red; }")
    (tmp_path / "font.woff2").write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0000000000000000000000000000000000000000000000000000000000000000\n"
        "size 12345\n"
    )

    with pytest.raises(RuntimeError, match=r"1 static file\(s\) are unresolved Git LFS pointers"):
        check_lfs_objects(tmp_path)


def test_check_lfs_objects_reports_every_broken_file(tmp_path: Path) -> None:
    """Test that the count in the error reflects every pointer stub found, not just the first."""
    pointer_content = "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1\n"
    (tmp_path / "one.png").write_text(pointer_content)
    (tmp_path / "two.woff2").write_text(pointer_content)

    with pytest.raises(RuntimeError, match=r"2 static file\(s\) are unresolved Git LFS pointers"):
        check_lfs_objects(tmp_path)
