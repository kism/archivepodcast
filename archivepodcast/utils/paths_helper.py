"""Helper for application paths."""

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
        self.app_directory = APP_DIRECTORY
        self.static_directory = self.app_directory / "static"
        self.template_directory = self.app_directory / "templates"

        # This should be the first time we know the web root
        local_file_cache.refresh(self.web_root)
