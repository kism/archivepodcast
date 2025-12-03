"""Instance of application paths helper."""

from pathlib import Path

from archivepodcast.utils.paths_helper import AppPathsHelper

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
