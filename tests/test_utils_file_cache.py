from pathlib import Path

import pytest

from archivepodcast.utils.file_cache import LocalFileCache


def test_local_file_cache_init() -> None:
    """Test that LocalFileCache initializes with None files."""
    cache = LocalFileCache()
    assert cache._files is None


def test_refresh_populates_cache(tmp_path: Path) -> None:
    """Test that refresh() correctly populates the cache with files."""
    # Create a test directory structure
    web_root = tmp_path / "web_root"
    web_root.mkdir()

    test_files: list[Path] = [web_root / "file1.txt", web_root / "file2.txt", web_root / "subdir" / "file3.txt"]

    for file in test_files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()

    cache = LocalFileCache()
    cache.refresh(web_root)

    # Test that get_all() returns correct Path objects
    files = cache.get_all()
    assert len(files) == len(test_files)

    for file in test_files:
        assert file.relative_to(web_root) in files

    # Test that get_all_str() returns correct string paths
    files_str = cache.get_all_str()
    assert isinstance(files_str, list)
    assert all(isinstance(f, str) for f in files_str)
    for file in test_files:
        assert str(file.relative_to(web_root)) in files_str


def test_refresh_sorts_files(tmp_path: Path) -> None:
    """Test that refresh() sorts the files alphabetically."""
    web_root = tmp_path / "web_root"
    web_root.mkdir()

    test_files: list[Path] = [web_root / "zebra.txt", web_root / "alpha.txt", web_root / "beta.txt"]

    for file in test_files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()

    cache = LocalFileCache()
    cache.refresh(web_root)

    files = cache.get_all()
    assert files == [Path("alpha.txt"), Path("beta.txt"), Path("zebra.txt")]


def test_raises_error_when_not_initialized() -> None:
    """Test that get_all_str() raises ValueError when cache is not initialized."""
    cache = LocalFileCache()

    match_text = r"File cache is not initialized. Call refresh\(\) first."

    with pytest.raises(ValueError, match=match_text):
        cache.get_all_str()

    with pytest.raises(ValueError, match=match_text):
        cache.get_all()

    with pytest.raises(ValueError, match=match_text):
        cache.check_exists(Path("somefile.txt"))

    with pytest.raises(ValueError, match=match_text):
        cache.add_file(Path("somefile.txt"))


def test_check_exists_returns_true_for_cached_file(tmp_path: Path) -> None:
    """Test that check_exists() returns True for files in the cache."""
    web_root = tmp_path / "web_root"
    web_root.mkdir()
    (web_root / "exists.txt").touch()

    cache = LocalFileCache()
    cache.refresh(web_root)

    assert cache.check_exists(Path("exists.txt")) is True
    assert cache.check_exists(Path("nonexistent.txt")) is False


def test_add_file_adds_new_file(tmp_path: Path) -> None:
    """Test that add_file() adds a new file to the cache."""
    web_root = tmp_path / "web_root"
    web_root.mkdir()
    (web_root / "existing.txt").touch()

    cache = LocalFileCache()
    cache.refresh(web_root)

    new_file = Path("new_file.txt")
    cache.add_file(new_file)

    files = cache.get_all()
    assert new_file in files
    assert len(files) == 2

    # Check dupilcates are not added
    cache.add_file(new_file)
    files = cache.get_all()
    assert len(files) == 2


def test_relative_paths_are_used(tmp_path: Path) -> None:
    """Test that cached paths are relative to web_root."""
    web_root = tmp_path / "web_root"
    web_root.mkdir()
    (web_root / "file.txt").touch()

    cache = LocalFileCache()
    cache.refresh(web_root)

    files = cache.get_all()
    # Ensure paths are relative, not absolute
    assert all(not f.is_absolute() for f in files)
    assert Path("file.txt") in files
