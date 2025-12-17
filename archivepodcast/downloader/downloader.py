"""Download and process podcast feeds and media files."""
# and return xml that can be served to download them

import contextlib
import datetime
import re
import time
from http import HTTPStatus

import aiohttp

from archivepodcast.archiver.rss_models import (
    AtomLink,
    Channel,
    Enclosure,
    Image,
    Item,
    ItunesImage,
    ItunesOwner,
    MediaContent,
    RssFeed,
)
from archivepodcast.constants import XML_ENCODING
from archivepodcast.instances.health import health
from archivepodcast.utils.log_messages import log_aiohttp_exception
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.time import warn_if_too_long

from .asset_downloader import AssetDownloader
from .constants import AUDIO_FORMATS, DOWNLOAD_RETRY_COUNT, IMAGE_FORMATS
from .helpers import delay_download

logger = get_logger(__name__)


class PodcastsDownloader(AssetDownloader):
    """PodcastDownloader object."""

    async def download_podcast(
        self,
    ) -> RssFeed | None:
        """Parse the rss, Download all the assets, this is main. Returns RssFeed."""
        self._feed_download_healthy = True
        feed_rss_healthy = True
        feed = await self._download_and_parse_rss()

        if feed and feed.is_valid:
            if not feed.has_episodes():
                # Log the whole feed
                rss_content = feed.to_bytes().decode(XML_ENCODING)
                logger.critical(
                    "[%s] Downloaded podcast rss has no episodes, full rss:\n%s",
                    self._podcast.name_one_word,
                    rss_content,
                )
                logger.error(
                    "Downloaded podcast rss %s has no episodes, not writing to disk", self._podcast.name_one_word
                )
                feed_rss_healthy = False
            else:
                # Write rss to disk
                rss_bytes = feed.to_bytes(encoding=XML_ENCODING)
                self._rss_file_path.write_bytes(rss_bytes)
                logger.debug("[%s] Wrote rss to disk: %s", self._podcast.name_one_word, self._rss_file_path)
        else:
            feed_rss_healthy = False
            logger.error("Unable to download podcast, something is wrong, will try to load from file")

        if not feed_rss_healthy:
            self._feed_download_healthy = False

        health.update_podcast_status(
            self._podcast.name_one_word,
            healthy_feed=feed_rss_healthy,
            healthy_download=self._feed_download_healthy,
        )

        return feed if feed and feed_rss_healthy else None

    async def _download_and_parse_rss(self) -> RssFeed | None:
        """Download and parse the podcast RSS feed, returning RssFeed."""
        content = None
        for n in range(DOWNLOAD_RETRY_COUNT):
            start_time = time.time()
            content, status = await self._fetch_podcast_rss()
            warn_if_too_long(f"[{self._podcast.name_one_word}] download podcast rss", time.time() - start_time)

            if status in {HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN}:
                logger.error(
                    "[%s] RSS download attempt failed with HTTP status %s, not retrying",
                    self._podcast.name_one_word,
                    status,
                )
                return None
            if status not in {HTTPStatus.OK, HTTPStatus.MOVED_PERMANENTLY, HTTPStatus.FOUND}:
                logger.warning(
                    "[%s] RSS download attempt %d/%d failed with HTTP status %s",
                    self._podcast.name_one_word,
                    n + 1,
                    DOWNLOAD_RETRY_COUNT,
                    status,
                )
            if content is not None:
                break
            await delay_download(n)

        if content is None:
            return None

        logger.debug("[%s] Success fetching podcast RSS", self._podcast.name_one_word)

        feed = RssFeed.from_bytes(content)
        if not feed.is_valid:
            logger.error(
                "[%s] Downloaded podcast rss (length %d) is not valid XML, cannot process podcast feed",
                self._podcast.name_one_word,
                len(content),
            )
            self._feed_download_healthy = False
            return None

        logger.debug("[%s] Downloaded rss feed, processing", self._podcast.name_one_word)
        logger.trace(str(feed.rss))

        if feed.rss and feed.rss.channel:
            await self._process_podcast_rss(feed.rss.channel)

        return feed

    async def _fetch_podcast_rss(self) -> tuple[bytes | None, HTTPStatus | None]:
        """Fetch the podcast RSS feed."""
        logger.debug(
            "[%s] Starting fetch for podcast RSS: %s", self._podcast.name_one_word, self._podcast.url.encoded_string()
        )
        try:
            async with self._aiohttp_session.get(self._podcast.url.encoded_string()) as response:
                return await response.read(), HTTPStatus(response.status)

        except aiohttp.ClientError as e:
            log_aiohttp_exception(self._podcast.name_one_word, self._podcast.url.encoded_string(), e, logger)
        return None, None

    # region RSS Hell

    async def _process_podcast_rss(self, channel: Channel) -> None:
        """Process the podcast rss channel and update it with new values."""
        # Update channel-level properties
        await self._process_channel(channel)

    async def _process_channel(self, channel: Channel) -> None:
        """Process channel properties and update with new values."""
        # Update basic channel properties
        self._handle_link(channel)
        self._handle_title(channel)
        self._handle_description(channel)

        # Update Atom link
        if channel.atom_link:
            self._handle_atom_link(channel.atom_link)

        # Update iTunes properties
        if channel.itunes_owner:
            self._handle_itunes_owner(channel.itunes_owner)
        if channel.itunes_author:
            channel.itunes_author = self._podcast.new_name if self._podcast.new_name else channel.itunes_author
        if channel.itunes_new_feed_url:
            channel.itunes_new_feed_url = (
                self._app_config.inet_path.encoded_string() + "rss/" + self._podcast.name_one_word
            )

        # Update iTunes image
        if channel.itunes_image:
            await self._handle_itunes_image(channel.itunes_image)

        # Update standard image
        if channel.image:
            await self._handle_image(channel.image)

        # Process all items/episodes
        for item in channel.items:
            await self._handle_item(item)

    def _handle_link(self, channel: Channel) -> None:
        """Handle the link property in the podcast channel."""
        logger.trace("[%s] Podcast link: %s", self._podcast.name_one_word, str(channel.link))
        channel.link = self._app_config.inet_path.encoded_string()

    def _handle_title(self, channel: Channel) -> None:
        """Handle the title property in the podcast channel."""
        logger.debug("[%s] Source Podcast title: %s", self._podcast.name_one_word, str(channel.title))
        if self._podcast.new_name != "":
            channel.title = self._podcast.new_name

    def _handle_description(self, channel: Channel) -> None:
        """Handle the description property in the podcast channel."""
        logger.trace("[%s] Podcast description: %s", self._podcast.name_one_word, str(channel.description))
        channel.description = self._podcast.description

    def _handle_atom_link(self, atom_link: AtomLink) -> None:
        """Handle the Atom link in the podcast channel."""
        logger.trace("[%s] Atom link: %s", self._podcast.name_one_word, str(atom_link.href))
        atom_link.href = self._app_config.inet_path.encoded_string() + "rss/" + self._podcast.name_one_word

    def _handle_itunes_owner(self, owner: ItunesOwner) -> None:
        """Handle the iTunes owner in the podcast channel."""
        logger.trace("[%s] iTunes owner: %s / %s", self._podcast.name_one_word, owner.name, owner.email)
        if self._podcast.new_name == "" and owner.name:
            self._podcast.new_name = owner.name
        owner.name = self._podcast.new_name

        if self._podcast.contact_email == "" and owner.email:
            self._podcast.contact_email = owner.email
        owner.email = self._podcast.contact_email

    async def _handle_itunes_image(self, itunes_image: ItunesImage) -> None:
        """Handle the iTunes image in the podcast channel."""
        logger.trace("[%s] iTunes image: %s", self._podcast.name_one_word, str(itunes_image.href))
        title = self._cleanup_file_name(self._podcast.new_name)
        url = itunes_image.href
        logger.trace("[%s] Image URL: %s", self._podcast.name_one_word, url)
        for filetype in IMAGE_FORMATS:
            if filetype in url:
                await self._download_cover_art(url, title, filetype)
                itunes_image.href = (
                    self._app_config.inet_path.encoded_string()
                    + "content/"
                    + self._podcast.name_one_word
                    + "/"
                    + title
                    + filetype
                )

    async def _handle_image(self, image: Image) -> None:
        """Handle the image element in the podcast channel."""
        logger.trace("[%s] Image title: %s", self._podcast.name_one_word, str(image.title))
        image.title = self._podcast.new_name
        image.link = self._app_config.inet_path.encoded_string()

        if image.url:
            title = self._cleanup_file_name(self._podcast.new_name)
            url = image.url
            for filetype in IMAGE_FORMATS:
                if filetype in url:
                    await self._download_asset(url, title, filetype)
                    image.url = (
                        self._app_config.inet_path.encoded_string()
                        + "content/"
                        + self._podcast.name_one_word
                        + "/"
                        + title
                        + filetype
                    )

    async def _handle_item(self, item: Item) -> None:
        """Handle an item/episode in the podcast feed."""
        file_date_string = self._get_file_date_string(item)
        title = item.title or ""
        logger.trace("Episode title: %s", title)

        # Handle enclosure (audio file)
        if item.enclosure:
            await self._handle_enclosure(item.enclosure, title, file_date_string)

        # Handle media:content (alternative to enclosure)
        if item.media_content:
            await self._handle_media_content(item.media_content, title, file_date_string)

        # Handle episode image
        if item.itunes_image:
            await self._handle_episode_image(item.itunes_image, title, file_date_string)

    async def _handle_enclosure(self, enclosure: Enclosure, title: str, file_date_string: str) -> None:
        """Handle the enclosure element in an episode."""
        logger.trace("Enclosure, URL: %s", enclosure.url)
        title = self._cleanup_file_name(title)
        url = enclosure.url
        enclosure.url = ""
        for audio_format in AUDIO_FORMATS:
            new_audio_format = audio_format
            if audio_format in url:
                if audio_format == ".wav":
                    new_length = await self._handle_wav(url, title, audio_format, file_date_string)
                    new_audio_format = ".mp3"
                    enclosure.type = "audio/mpeg"
                    enclosure.length = str(new_length)
                else:
                    await self._download_asset(url, title, audio_format, file_date_string)
                enclosure.url = (
                    self._app_config.inet_path.encoded_string()
                    + "content/"
                    + self._podcast.name_one_word
                    + "/"
                    + file_date_string
                    + "-"
                    + title
                    + new_audio_format
                )

    async def _handle_media_content(self, media_content: MediaContent, title: str, file_date_string: str) -> None:
        """Handle the media:content element in an episode."""
        # Media content is similar to enclosure, reuse same logic
        logger.trace("Media content, URL: %s", media_content.url)
        title = self._cleanup_file_name(title)
        url = media_content.url
        media_content.url = ""
        for audio_format in AUDIO_FORMATS:
            new_audio_format = audio_format
            if audio_format in url:
                if audio_format == ".wav":
                    new_length = await self._handle_wav(url, title, audio_format, file_date_string)
                    new_audio_format = ".mp3"
                    media_content.type = "audio/mpeg"
                    media_content.length = str(new_length)
                else:
                    await self._download_asset(url, title, audio_format, file_date_string)
                media_content.url = (
                    self._app_config.inet_path.encoded_string()
                    + "content/"
                    + self._podcast.name_one_word
                    + "/"
                    + file_date_string
                    + "-"
                    + title
                    + new_audio_format
                )

    async def _handle_episode_image(
        self,
        itunes_image: ItunesImage,
        title: str,
        file_date_string: str,
    ) -> None:
        """Handle the episode image in an episode."""
        title = self._cleanup_file_name(title)
        url = itunes_image.href
        for filetype in IMAGE_FORMATS:
            if filetype in url:
                await self._download_asset(url, title, filetype, file_date_string)
                itunes_image.href = (
                    self._app_config.inet_path.encoded_string()
                    + "content/"
                    + self._podcast.name_one_word
                    + "/"
                    + file_date_string
                    + "-"
                    + title
                    + filetype
                )

    # region Helpers

    def _cleanup_file_name(self, file_name: str | bytes) -> str:
        """Convert a file name into a URL-safe slug format.

        Standardizes names by removing common podcast prefixes/suffixes and
        converting to hyphenated lowercase alphanumeric format.
        """
        if isinstance(file_name, bytes):
            file_name = file_name.decode()

        # Standardise
        file_name = file_name.replace("[AUDIO]", "")
        file_name = file_name.replace("[Audio]", "")
        file_name = file_name.replace("[audio]", "")
        file_name = file_name.replace("AUDIO", "")
        file_name = file_name.replace("(Audio Only)", "")
        file_name = file_name.replace("(Audio only)", "")
        file_name = file_name.replace("Ep. ", "Ep ")
        file_name = file_name.replace("Ep: ", "Ep ")
        file_name = file_name.replace("Episode ", "Ep ")
        file_name = file_name.replace("Episode: ", "Ep ")

        # Generate Slug, everything that isn't alphanumeric is now a hyphen
        file_name = re.sub(r"[^a-zA-Z0-9-]", " ", file_name)

        # Remove excess spaces
        while "  " in file_name:
            file_name = file_name.replace("  ", " ")

        # Replace spaces with hyphens
        file_name = file_name.strip()
        file_name = file_name.replace(" ", "-")

        logger.trace("[%s] Clean Filename: '%s'", self._podcast.name_one_word, file_name)
        return file_name

    def _get_file_date_string(self, item: Item) -> str:
        """Get the file date string from the item."""
        file_date_string = "00000000"
        if item.pub_date:
            original_date = item.pub_date
            file_date = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
            with contextlib.suppress(ValueError):
                file_date = datetime.datetime.strptime(original_date, "%a, %d %b %Y %H:%M:%S %Z")  # noqa: DTZ007 This is how some feeds format their time
            with contextlib.suppress(ValueError):
                file_date = datetime.datetime.strptime(original_date, "%a, %d %b %Y %H:%M:%S %z")
            file_date_string = file_date.strftime("%Y%m%d")
        return file_date_string
