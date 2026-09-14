"""Helper for application paths, and its instance."""

from pathlib import Path

from archivepodcast.constants import APP_DIRECTORY
from archivepodcast.instances.path_cache import local_file_cache
from archivepodcast.utils.lfs_check import check_lfs_objects


class AppPathsHelper:
    """Helper for application paths."""

    def __init__(self, instance_path: Path) -> None:
        """Setup the application paths."""
        self.instance_path = Path(instance_path)
        self.web_root: Path = self.instance_path / "web"  # This gets used so often, it's worth the variable
        self.static_directory: Path = APP_DIRECTORY / "static"

        check_lfs_objects(self.static_directory)

        # This should be the first time we know the web root
        local_file_cache.refresh(self.web_root)


_app_paths: AppPathsHelper | None = None


def get_app_paths(instance_path: Path | None = None) -> AppPathsHelper:
    """Get the application paths helper instance."""
    global _app_paths  # ruff: ignore[global-statement]
    if _app_paths is None:
        if instance_path is None:
            msg = "Application paths helper instance has not been set."
            raise RuntimeError(msg)

        _app_paths = AppPathsHelper(instance_path)
    return _app_paths
