"""Download and process podcast feeds and media files."""
# and return xml that can be served to download them

import contextlib
import datetime
import re
import time
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiohttp
from lxml import etree

from archivepodcast.config import AppConfig, PodcastConfig
from archivepodcast.instances.health import health
from archivepodcast.utils.log_messages import log_aiohttp_exception
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.rss import tree_no_episodes
from archivepodcast.utils.time import warn_if_too_long

from .asset_downloader import AssetDownloader
from .constants import AUDIO_FORMATS, DOWNLOAD_RETRY_COUNT, IMAGE_FORMATS
from .helpers import delay_download

if TYPE_CHECKING:
    from archivepodcast.config import AppConfig, PodcastConfig  # pragma: no cover
else:
    AppConfig = object
    PodcastConfig = object

logger = get_logger(__name__)


# These make the name spaces appear nicer in the generated XML
etree.register_namespace("googleplay", "http://www.google.com/schemas/play-podcasts/1.0")
etree.register_namespace("atom", "http://www.w3.org/2005/Atom")
etree.register_namespace("podcast", "https://podcastindex.org/namespace/1.0")
etree.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
etree.register_namespace("media", "http://search.yahoo.com/mrss/")
etree.register_namespace("sy", "http://purl.org/rss/1.0/modules/syndication/")
etree.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
etree.register_namespace("wfw", "http://wellformedweb.org/CommentAPI/")
etree.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
etree.register_namespace("slash", "http://purl.org/rss/1.0/modules/slash/")
etree.register_namespace("rawvoice", "http://www.rawvoice.com/rawvoiceRssModule/")
etree.register_namespace("spotify", "http://www.spotify.com/ns/rss/")
etree.register_namespace("feedburner", "http://rssnamespace.org/feedburner/ext/1.0")


class PodcastsDownloader(AssetDownloader):
    """PodcastDownloader object."""

    async def download_podcast(
        self,
    ) -> etree._ElementTree | None:
        """Parse the rss, Download all the assets, this is main."""
        self._feed_download_healthy = True
        feed_rss_healthy = True
        tree = await self._download_and_parse_rss()

        if tree:
            if tree_no_episodes(tree):
                logger.error(
                    "Downloaded podcast rss %s has no episodes, not writing to disk", self._podcast.name_one_word
                )
                feed_rss_healthy = False
            else:
                # Write rss to disk
                tree.write(
                    str(self._rss_file_path),
                    encoding="utf-8",
                    xml_declaration=True,
                )
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

        return tree

    async def _download_and_parse_rss(self) -> etree._ElementTree | None:
        """Download and parse the podcast RSS feed."""
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

        try:
            podcast_rss = etree.fromstring(content)
        except etree.XMLSyntaxError:
            logger.error(  # noqa: TRY400
                "[%s] Downloaded podcast rss (length %d) is not valid XML, cannot process podcast feed",
                self._podcast.name_one_word,
                len(content),
            )
            self._feed_download_healthy = False
            return None
        podcast_rss = etree.fromstring(content)
        logger.debug("[%s] Downloaded rss feed, processing", self._podcast.name_one_word)
        logger.trace(str(podcast_rss))

        xml_first_child = podcast_rss[0]
        await self._process_podcast_rss(xml_first_child)
        podcast_rss[0] = xml_first_child

        return etree.ElementTree(podcast_rss)

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

    async def _process_podcast_rss(self, xml_first_child: etree._Element) -> None:
        """Process the podcast rss and update it with new values."""
        for channel in xml_first_child:
            await self._process_channel_tag(channel)

    async def _process_channel_tag(self, channel: etree._Element) -> None:  # noqa: C901 # There is no way to avoid this really, there are many tag types
        """Process individual channel tags in the podcast rss."""
        match channel.tag:
            case "link":
                self._handle_link_tag(channel)
            case "title":
                self._handle_title_tag(channel)
            case "description":
                self._handle_description_tag(channel)
            case "{http://www.w3.org/2005/Atom}link":
                self._handle_atom_link_tag(channel)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}owner":
                self._handle_itunes_owner_tag(channel)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}author":
                self._handle_itunes_author_tag(channel)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}new-feed-url":
                self._handle_itunes_new_feed_url_tag(channel)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
                await self._handle_itunes_image_tag(channel)
            case "image":
                await self._handle_image_tag(channel)
            case "item":
                await self._handle_item_tag(channel)
            case _:
                logger.trace(
                    "[%s] Unhandled root-level XML tag %s, (under channel.tag) leaving as-is",
                    self._podcast.name_one_word,
                    channel.tag,
                )

    def _handle_link_tag(self, channel: etree._Element) -> None:
        """Handle the link tag in the podcast rss."""
        logger.trace("[%s] Podcast link: %s", self._podcast.name_one_word, str(channel.text))
        channel.text = self._app_config.inet_path.encoded_string()

    def _handle_title_tag(self, channel: etree._Element) -> None:
        """Handle the title tag in the podcast rss."""
        logger.debug("[%s] Source Podcast title: %s", self._podcast.name_one_word, str(channel.text))
        if self._podcast.new_name != "":
            channel.text = self._podcast.new_name

    def _handle_description_tag(self, channel: etree._Element) -> None:
        """Handle the description tag in the podcast rss."""
        logger.trace("[%s] Podcast description: %s", self._podcast.name_one_word, str(channel.text))
        channel.text = self._podcast.description

    def _handle_atom_link_tag(self, channel: etree._Element) -> None:
        """Handle the Atom link tag in the podcast rss."""
        logger.trace("[%s] Atom link: %s", self._podcast.name_one_word, str(channel.attrib["href"]))
        channel.attrib["href"] = self._app_config.inet_path.encoded_string() + "rss/" + self._podcast.name_one_word
        channel.text = " "

    def _handle_itunes_owner_tag(self, channel: etree._Element) -> None:
        """Handle the iTunes owner tag in the podcast rss."""
        logger.trace("[%s] iTunes owner: %s", self._podcast.name_one_word, str(channel.text))
        for child in channel:
            if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}name":
                if self._podcast.new_name == "":
                    self._podcast.new_name = child.text or ""
                child.text = self._podcast.new_name
            if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}email":
                if self._podcast.contact_email == "":
                    self._podcast.contact_email = child.text or ""
                child.text = self._podcast.contact_email

    def _handle_itunes_author_tag(self, channel: etree._Element) -> None:
        """Handle the iTunes author tag in the podcast rss."""
        logger.trace("[%s] iTunes author: %s", self._podcast.name_one_word, str(channel.text))
        if self._podcast.new_name != "":
            channel.text = self._podcast.new_name

    def _handle_itunes_new_feed_url_tag(self, channel: etree._Element) -> None:
        """Handle the iTunes new-feed-url tag in the podcast rss."""
        logger.trace("[%s] iTunes new-feed-url: %s", self._podcast.name_one_word, str(channel.text))
        channel.text = self._app_config.inet_path.encoded_string() + "rss/" + self._podcast.name_one_word

    async def _handle_itunes_image_tag(self, channel: etree._Element) -> None:
        """Handle the iTunes image tag in the podcast rss."""
        logger.trace("[%s] iTunes image: %s", self._podcast.name_one_word, str(channel.attrib["href"]))
        title = self._cleanup_file_name(self._podcast.new_name)
        url = channel.attrib.get("href", "")
        logger.trace("[%s] Image URL: %s", self._podcast.name_one_word, url)
        for filetype in IMAGE_FORMATS:
            if filetype in url:
                await self._download_cover_art(url, title, filetype)
                channel.attrib["href"] = (
                    self._app_config.inet_path.encoded_string()
                    + "content/"
                    + self._podcast.name_one_word
                    + "/"
                    + title
                    + filetype
                )
        channel.text = " "

    async def _handle_image_tag(self, channel: etree._Element) -> None:
        """Handle the image tag in the podcast rss."""
        for child in channel:
            logger.trace("[%s] image > XML tag: %s", self._podcast.name_one_word, child.tag)
            if child.tag == "title":
                logger.trace("[%s] Image title: %s", self._podcast.name_one_word, str(child.text))
                child.text = self._podcast.new_name
            elif child.tag == "link":
                child.text = self._app_config.inet_path.encoded_string()
            elif child.tag == "url":
                title = self._cleanup_file_name(self._podcast.new_name)
                url = child.text or ""
                for filetype in IMAGE_FORMATS:
                    if filetype in url:
                        await self._download_asset(url, title, filetype)
                        child.text = (
                            self._app_config.inet_path.encoded_string()
                            + "content/"
                            + self._podcast.name_one_word
                            + "/"
                            + title
                            + filetype
                        )
        channel.text = " "

    async def _handle_item_tag(self, channel: etree._Element) -> None:
        """Handle the item tag in the podcast rss."""
        file_date_string = self._get_file_date_string(channel)
        title = ""
        for child in channel:
            if child.tag == "title":
                title = str(child.text)
                logger.trace("Episode title: %s", title)

        for child in channel:
            if child.tag == "enclosure" or "{http://search.yahoo.com/mrss/}content" in str(child.tag):
                await self._handle_enclosure_tag(child, title, file_date_string)
            elif child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
                await self._handle_episode_image_tag(child, title, file_date_string)

    async def _handle_enclosure_tag(self, child: etree._Element, title: str, file_date_string: str) -> None:
        """Handle the enclosure tag in the podcast rss."""
        logger.trace("Enclosure, URL: %s", child.attrib.get("url", ""))
        title = self._cleanup_file_name(title)
        url = child.attrib.get("url", "")
        child.attrib["url"] = ""
        for audio_format in AUDIO_FORMATS:
            new_audio_format = audio_format
            if audio_format in url:
                if audio_format == ".wav":
                    new_length = await self._handle_wav(url, title, audio_format, file_date_string)
                    new_audio_format = ".mp3"
                    child.attrib["type"] = "audio/mpeg"
                    child.attrib["length"] = str(new_length)
                else:
                    await self._download_asset(url, title, audio_format, file_date_string)
                child.attrib["url"] = (
                    self._app_config.inet_path.encoded_string()
                    + "content/"
                    + self._podcast.name_one_word
                    + "/"
                    + file_date_string
                    + "-"
                    + title
                    + new_audio_format
                )

    async def _handle_episode_image_tag(self, child: etree._Element, title: str, file_date_string: str) -> None:
        """Handle the episode image tag in the podcast rss."""
        title = self._cleanup_file_name(title)
        url = child.attrib.get("href", "")
        for filetype in IMAGE_FORMATS:
            if filetype in url:
                await self._download_cover_art(url, title, filetype)
                child.attrib["href"] = (
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

    def _get_file_date_string(self, channel: etree._Element) -> str:
        """Get the file date string from the channel."""
        file_date_string = "00000000"
        for child in channel:
            if child.tag == "pubDate":
                original_date = str(child.text)
                file_date = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
                with contextlib.suppress(ValueError):
                    file_date = datetime.datetime.strptime(original_date, "%a, %d %b %Y %H:%M:%S %Z")  # noqa: DTZ007 This is how some feeds format their time
                with contextlib.suppress(ValueError):
                    file_date = datetime.datetime.strptime(original_date, "%a, %d %b %Y %H:%M:%S %z")
                file_date_string = file_date.strftime("%Y%m%d")
        return file_date_string
