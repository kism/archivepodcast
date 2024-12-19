"""Archivepodcast health module."""

import json


class PodcastHealth:
    """Podcast Health object."""

    def __init__(self) -> None:
        """Initialise the Podcast Health object."""
        self.rss_available: bool = False
        self.rss_live: bool = False
        self.healthy: bool = False
        self.last_episode: str = "NOT IMPLEMENTED"


class WebpageHealth:
    """Webpage Health object."""

    def __init__(self) -> None:
        """Initialise the Webpage Health object."""
        self.last_rendered: int = 0

class CoreHealth:
    """Core Health object."""

    def __init__(self) -> None:
        """Initialise the Core Health object."""
        self.alive: bool = True
        self.last_run: int = 0


class PodcastArchiverHealth:
    """Podcast Archiver Health object."""

    def __init__(self) -> None:
        """Initialise the Podcast Archiver Health object."""
        self.core: CoreHealth = CoreHealth()
        self.podcasts: dict[str, PodcastHealth] = {}
        self.templates: dict[str, WebpageHealth] = {}


    def get_health(self) -> str:
        """Return the health."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def update_template_status(self, webpage: str, **kwargs: bool | str | int) -> None:
        """Update the webpage."""
        if webpage not in self.templates:
            self.templates[webpage] = WebpageHealth()

        for key, value in kwargs.items():
            if value is not None and hasattr(self.templates[webpage], key):
                setattr(self.templates[webpage], key, value)

    def update_podcast_status(self, podcast: str, **kwargs: bool | str | int) -> None:
        """Update the podcast."""
        if podcast not in self.podcasts:
            self.podcasts[podcast] = PodcastHealth()

        for key, value in kwargs.items():
            if value is not None and hasattr(self.podcasts[podcast], key):
                setattr(self.podcasts[podcast], key, value)

    def update_core_status(self, **kwargs: bool | str | int) -> None:
        """Update the core."""
        for key, value in kwargs.items():
            if value is not None and hasattr(self.core, key):
                setattr(self.core, key, value)
