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
        self.last_rendered: str = ""

class PodcastArchiverHealth:
    """Podcast Archiver Health object."""

    def __init__(self) -> None:
        """Initialise the Podcast Archiver Health object."""
        self.s3_enabled: bool = False
        self.podcasts: dict[str, PodcastHealth] = {}
        self.webpages: dict[str, WebpageHealth] = {}

    def get_health(self) -> str:
        """Return the health."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def update_template_status(self, webpage: str, last_rendered: str | None = None) -> None:
        """Update the webpage."""
        if webpage not in self.webpages:
            self.webpages[webpage] = WebpageHealth()

        if last_rendered is not None:
            self.webpages[webpage].last_rendered = last_rendered

    def update_podcast_status(
        self,
        podcast: str,
        rss_available: bool | None = None,
        rss_live: bool | None = None,
        last_episode: str | None = None,
        healthy: bool | None = None,
    ) -> None:
        """Update the podcast."""
        if podcast not in self.podcasts:
            self.podcasts[podcast] = PodcastHealth()

        if rss_available is not None:
            self.podcasts[podcast].rss_available = rss_available

        if rss_live is not None:
            self.podcasts[podcast].rss_live = rss_live

        if last_episode is not None:
            self.podcasts[podcast].last_episode = last_episode

        if healthy is not None:
            self.podcasts[podcast].healthy = healthy

    def update_s3_status(self, s3_enabled: bool | None = None) -> None:
        """Update the S3 status."""
        if s3_enabled is not None:
            self.s3_enabled = s3_enabled
