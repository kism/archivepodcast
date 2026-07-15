"""Helper for application paths, and its instance."""

from pathlib import Path

from archivepodcast.constants import APP_DIRECTORY
from archivepodcast.instances.path_cache import local_file_cache


class AppPathsHelper:
    """Helper for application paths."""

    def __init__(self, root_path: Path, instance_path: Path) -> None:
        """Setup the application paths."""
        self.root_path = Path(root_path)
        self.instance_path = Path(instance_path)
        self.web_root: Path = self.instance_path / "web"  # This gets used so often, it's worth the variable
        self.app_directory: Path = APP_DIRECTORY
        self.static_directory: Path = self.app_directory / "static"
        self.template_directory: Path = self.app_directory / "templates"

        # This should be the first time we know the web root
        local_file_cache.refresh(self.web_root)


_app_paths: AppPathsHelper | None = None


def get_app_paths(
    root_path: Path | None = None,
    instance_path: Path | None = None,
) -> AppPathsHelper:
    """Get the application paths helper instance."""
    global _app_paths  # noqa: PLW0603
    if _app_paths is None:
        if root_path is None or instance_path is None:
            msg = "Application paths helper instance has not been set."
            raise RuntimeError(msg)

        _app_paths = AppPathsHelper(root_path, instance_path)
    return _app_paths
