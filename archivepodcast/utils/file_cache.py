"""Module for local file caching functionality."""

from pathlib import Path


class LocalFileCache:
    """Class representing a local file cache."""

    def __init__(self) -> None:
        """Initialise the local file cache."""
        self._files: list[Path] | None = None

    def refresh(self, web_root: Path) -> None:
        """Refresh the local file cache."""
        self._files = [path.relative_to(web_root) for path in web_root.rglob("*") if path.is_file()]
        self._files.sort()

    def get_all(self) -> list[Path]:
        """Get all cached file paths."""
        if self._files is None:
            msg = "File cache is not initialized. Call refresh() first."
            raise ValueError(msg)
        return self._files

    def get_all_str(self) -> list[str]:
        """Get all cached file paths as strings."""
        return [str(path) for path in self.get_all()]

    def check_exists(self, file_path: Path) -> bool:
        """Check if a file path exists in the cache."""
        return file_path in self.get_all()

    def add_file(self, file_path: Path) -> None:
        """Add a new file path to the cache."""
        if self._files is None:
            msg = "File cache is not initialized. Call refresh() first."
            raise ValueError(msg)
        if file_path not in self._files:
            self._files.append(file_path)
            self._files.sort()
