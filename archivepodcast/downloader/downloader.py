"""Download and process podcast feeds and media files."""
# and return xml that can be served to download them

import contextlib
import datetime
import re
import shutil
import sys
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
import ffmpeg
from botocore.exceptions import (
    ClientError as S3ClientError,
)
from lxml import etree

from archivepodcast.config import AppConfig, PodcastConfig
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.s3 import list_all_s3_objects

from .constants import AUDIO_FORMATS, CONTENT_TYPES, FFMPEG_INFO, IMAGE_FORMATS

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # pragma: no cover
else:
    S3Client = object

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


def check_ffmpeg() -> None:
    """Check if ffmpeg is installed."""
    ffmpeg_paths = [
        Path("/usr/bin/ffmpeg"),
        Path("/usr/local/bin/ffmpeg"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
    ]
    found_manually = any(ffmpeg_path.exists() for ffmpeg_path in ffmpeg_paths)

    if not shutil.which("ffmpeg") and not found_manually:
        logger.error(FFMPEG_INFO)
        sys.exit(1)


check_ffmpeg()


class PodcastDownloader:
    """PodcastDownloader object."""

    def __init__(self, app_config: AppConfig, s3: S3Client | None, web_root: Path) -> None:
        """Initialise the PodcastDownloader object."""
        self.s3 = s3
        self.s3_paths_cache: list[str] = []
        self.local_paths_cache: list[Path] = []
        self.feed_download_healthy: bool = True  # Need to change this if you do one podcast download per thread
        self.app_config = app_config
        self.web_root = web_root
        self._session: aiohttp.ClientSession | None = None
        self.update_file_cache()

        logger.trace("PodcastDownloader config (re)loaded")

    def update_file_cache(self) -> None:
        """Update the file cache."""
        if self.s3:
            self.s3_paths_cache = []
            s3_paths = list_all_s3_objects(self.s3, self.app_config.s3.bucket)
            for s3_path in s3_paths:
                self.s3_paths_cache.append(s3_path["Key"])

            self.s3_paths_cache.sort()
        else:
            web_root = Path(self.web_root)
            self.local_paths_cache = [
                (path.relative_to(web_root)) for path in Path(self.web_root).rglob("*") if path.is_file()
            ]
            self.local_paths_cache.sort()

    def get_file_list(self) -> tuple[str, list[str]]:
        """Gets the base url and the file cache."""
        self.update_file_cache()

        base_url = self.app_config.s3.cdn_domain if self.s3 is not None else self.app_config.inet_path

        file_list = self.s3_paths_cache if self.s3 is not None else [str(path) for path in self.local_paths_cache]

        return base_url.encoded_string(), file_list

    def _get_session(self) -> aiohttp.ClientSession:
        """Start the aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=300), connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
            )

        return self._session

    async def download_podcast(self, podcast: PodcastConfig) -> tuple[etree._ElementTree | None, bool]:
        """Parse the rss, Download all the assets, this is main."""
        self.feed_download_healthy = True  # Until proven otherwise
        content = await self._fetch_podcast_rss(podcast.url.encoded_string())
        if content is None:
            return None, False

        podcast_rss = etree.fromstring(content)
        logger.info("📄 Downloaded rss feed, processing")
        logger.trace(str(podcast_rss))

        xml_first_child = podcast_rss[0]
        await self._process_podcast_rss(xml_first_child, podcast)
        podcast_rss[0] = xml_first_child

        return etree.ElementTree(podcast_rss), self.feed_download_healthy

    async def _fetch_podcast_rss(self, url: str) -> bytes | None:
        """Fetch the podcast rss from the given URL."""
        session = self._get_session()

        logger.debug("📜 Fetching podcast rss: %s", url)
        try:
            async with session.get(url) as response:
                if response.status != HTTPStatus.OK:
                    msg = f"❌ Not a great web response getting RSS: {response.status}\n{await response.text()}"
                    logger.error(msg)
                    return None

                logger.debug("📄 Success fetching podcast RSS: %s", response.status)
                return await response.read()

        except aiohttp.ClientError:
            logger.error("❌ Timeout fetching podcast rss: %s", url)  # noqa: TRY400

        return None

    async def _process_podcast_rss(self, xml_first_child: etree._Element, podcast: PodcastConfig) -> None:
        """Process the podcast rss and update it with new values."""
        for channel in xml_first_child:
            await self._process_channel_tag(channel, podcast)

    async def _process_channel_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:  # noqa: C901 # There is no way to avoid this really, there are many tag types
        """Process individual channel tags in the podcast rss."""
        match channel.tag:
            case "link":
                self._handle_link_tag(channel)
            case "title":
                self._handle_title_tag(channel, podcast)
            case "description":
                self._handle_description_tag(channel, podcast)
            case "{http://www.w3.org/2005/Atom}link":
                self._handle_atom_link_tag(channel, podcast)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}owner":
                self._handle_itunes_owner_tag(channel, podcast)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}author":
                self._handle_itunes_author_tag(channel, podcast)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}new-feed-url":
                self._handle_itunes_new_feed_url_tag(channel, podcast)
            case "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
                await self._handle_itunes_image_tag(channel, podcast)
            case "image":
                await self._handle_image_tag(channel, podcast)
            case "item":
                await self._handle_item_tag(channel, podcast)
            case _:
                logger.trace("Unhandled root-level XML tag %s, (under channel.tag) leaving as-is", channel.tag)

    def _handle_link_tag(self, channel: etree._Element) -> None:
        """Handle the link tag in the podcast rss."""
        logger.trace("Podcast link: %s", str(channel.text))
        channel.text = self.app_config.inet_path.encoded_string()

    def _handle_title_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the title tag in the podcast rss."""
        logger.info("📄 Source Podcast title: %s", str(channel.text))
        if podcast.new_name != "":
            channel.text = podcast.new_name

    def _handle_description_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the description tag in the podcast rss."""
        logger.trace("Podcast description: %s", str(channel.text))
        channel.text = podcast.description

    def _handle_atom_link_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the Atom link tag in the podcast rss."""
        logger.trace("Atom link: %s", str(channel.attrib["href"]))
        channel.attrib["href"] = self.app_config.inet_path.encoded_string() + "rss/" + podcast.name_one_word
        channel.text = " "

    def _handle_itunes_owner_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the iTunes owner tag in the podcast rss."""
        logger.trace("iTunes owner: %s", str(channel.text))
        for child in channel:
            if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}name":
                if podcast.new_name == "":
                    podcast.new_name = child.text or ""
                child.text = podcast.new_name
            if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}email":
                if podcast.contact_email == "":
                    podcast.contact_email = child.text or ""
                child.text = podcast.contact_email

    def _handle_itunes_author_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the iTunes author tag in the podcast rss."""
        logger.trace("iTunes author: %s", str(channel.text))
        if podcast.new_name != "":
            channel.text = podcast.new_name

    def _handle_itunes_new_feed_url_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the iTunes new-feed-url tag in the podcast rss."""
        logger.trace("iTunes new-feed-url: %s", str(channel.text))
        channel.text = self.app_config.inet_path.encoded_string() + "rss/" + podcast.name_one_word

    async def _handle_itunes_image_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the iTunes image tag in the podcast rss."""
        logger.trace("iTunes image: %s", str(channel.attrib["href"]))

        title = self._cleanup_file_name(podcast.new_name)
        url = channel.attrib.get("href", "")
        logger.trace("Image URL: %s", url)
        for filetype in IMAGE_FORMATS:
            if filetype in url:
                await self._download_cover_art(url, title, podcast, filetype)
                channel.attrib["href"] = (
                    self.app_config.inet_path.encoded_string()
                    + "content/"
                    + podcast.name_one_word
                    + "/"
                    + title
                    + filetype
                )
        channel.text = " "

    async def _handle_image_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the image tag in the podcast rss."""
        for child in channel:
            logger.trace("image > XML tag: %s", child.tag)
            if child.tag == "title":
                logger.trace("Image title: %s", str(child.text))
                child.text = podcast.new_name
            elif child.tag == "link":
                child.text = self.app_config.inet_path.encoded_string()
            elif child.tag == "url":
                title = self._cleanup_file_name(podcast.new_name)
                url = child.text or ""
                for filetype in IMAGE_FORMATS:
                    if filetype in url:
                        await self._download_asset(url, title, podcast, filetype)
                        child.text = (
                            self.app_config.inet_path.encoded_string()
                            + "content/"
                            + podcast.name_one_word
                            + "/"
                            + title
                            + filetype
                        )
        channel.text = " "

    async def _handle_item_tag(self, channel: etree._Element, podcast: PodcastConfig) -> None:
        """Handle the item tag in the podcast rss."""
        file_date_string = self._get_file_date_string(channel)
        title = ""
        for child in channel:
            if child.tag == "title":
                title = str(child.text)
                logger.debug("📢 Episode title: %s", title)

        for child in channel:
            if child.tag == "enclosure" or "{http://search.yahoo.com/mrss/}content" in str(child.tag):
                await self._handle_enclosure_tag(child, title, podcast, file_date_string)
            elif child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
                await self._handle_episode_image_tag(child, title, podcast, file_date_string)

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

    async def _handle_enclosure_tag(
        self, child: etree._Element, title: str, podcast: PodcastConfig, file_date_string: str
    ) -> None:
        """Handle the enclosure tag in the podcast rss."""
        logger.trace("Enclosure, URL: %s", child.attrib.get("url", ""))
        title = self._cleanup_file_name(title)
        url = child.attrib.get("url", "")
        child.attrib["url"] = ""
        for audio_format in AUDIO_FORMATS:
            new_audio_format = audio_format
            if audio_format in url:
                if audio_format == ".wav":
                    new_length = await self._handle_wav(url, title, podcast, audio_format, file_date_string)
                    new_audio_format = ".mp3"
                    child.attrib["type"] = "audio/mpeg"
                    child.attrib["length"] = str(new_length)
                else:
                    await self._download_asset(url, title, podcast, audio_format, file_date_string)
                child.attrib["url"] = (
                    self.app_config.inet_path.encoded_string()
                    + "content/"
                    + podcast.name_one_word
                    + "/"
                    + file_date_string
                    + "-"
                    + title
                    + new_audio_format
                )

    async def _handle_episode_image_tag(
        self, child: etree._Element, title: str, podcast: PodcastConfig, file_date_string: str
    ) -> None:
        """Handle the episode image tag in the podcast rss."""
        title = self._cleanup_file_name(title)
        url = child.attrib.get("href", "")
        for filetype in IMAGE_FORMATS:
            if filetype in url:
                await self._download_asset(url, title, podcast, filetype, file_date_string)
                child.attrib["href"] = (
                    self.app_config.inet_path.encoded_string()
                    + "content/"
                    + podcast.name_one_word
                    + "/"
                    + file_date_string
                    + "-"
                    + title
                    + filetype
                )

    def _check_local_path_exists(self, file_path: Path) -> bool:
        """Check if the file exists locally."""
        file_exists = file_path.is_file()

        if file_exists:
            self._append_to_local_paths_cache(file_path)
            logger.debug("📁 File: %s exists locally", file_path)
        else:
            logger.debug("📁 File: %s does not exist locally", file_path)

        return file_exists

    def _check_path_exists(self, file_path: Path | str) -> bool:
        """Check the path, s3 or local."""
        file_exists = False

        if self.s3 is not None:
            # Convert file_path to a Path object if it isn't already
            file_path = Path(file_path)

            # If it's an absolute path and under web_root, make it relative to web_root
            if file_path.is_absolute() and file_path.is_relative_to(self.web_root):
                file_path = file_path.relative_to(self.web_root)

            # Convert to a posix path (forward slashes) and ensure no leading slash
            s3_key = file_path.as_posix().lstrip("/")

            if s3_key not in self.s3_paths_cache:
                try:
                    # Head object to check if file exists
                    self.s3.head_object(Bucket=self.app_config.s3.bucket, Key=s3_key)
                    logger.debug(
                        "⛅ File: %s exists in s3 bucket",
                        s3_key,
                    )
                    self.s3_paths_cache.append(s3_key)
                    file_exists = True

                except S3ClientError as e:
                    if e.response.get("Error", {}).get("Code") == "404":
                        logger.debug(
                            "⛅ File: %s does not exist 🙅‍ in the s3 bucket",
                            s3_key,
                        )
                    else:
                        logger.exception("⛅❌ s3 check file exists errored out?")
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception("⛅❌ Unhandled s3 Error:")

            else:
                logger.trace("s3 path %s exists in s3_paths_cache, skipping", s3_key)
                file_exists = True

        else:
            if not isinstance(file_path, Path):
                file_path = Path(file_path)
            file_exists = self._check_local_path_exists(file_path)

        return file_exists

    async def _handle_wav(
        self, url: str, title: str, podcast: PodcastConfig, extension: str = "", file_date_string: str = ""
    ) -> int:
        """Convert podcasts that have wav episodes 😔. Returns new file length."""
        logger.trace("🎵 Handling wav file: %s", title)
        new_length = None
        spacer = ""  # This logic can be removed since WAVs will always have a date
        if file_date_string != "":
            spacer = "-"

        content_dir = Path(self.web_root) / "content" / podcast.name_one_word
        wav_file_path: Path = content_dir / f"{file_date_string}{spacer}{title}.wav"
        mp3_file_path: Path = content_dir / f"{file_date_string}{spacer}{title}.mp3"

        # If we need do download and convert a wav there is a small chance
        # the user has had ffmpeg issues, remove existing files to play it safe
        if wav_file_path.exists():
            with contextlib.suppress(Exception):
                wav_file_path.unlink()
                mp3_file_path.unlink()

        # If the asset hasn't already been downloaded and converted
        if not self._check_path_exists(mp3_file_path):
            await self._download_asset(
                url,
                title,
                podcast,
                extension,
                file_date_string,
            )

            logger.info("♻ Converting episode %s to mp3", title)
            logger.debug("♻ MP3 File Path: %s", mp3_file_path)

            input_wav = ffmpeg.input(filename=wav_file_path)
            ff = ffmpeg.output(
                input_wav,
                filename=mp3_file_path,
                codec="libmp3lame",
                aq="4",
            )  # VBR v4 might be overkill for voice buy I pick it

            ff.run()

            logger.info("♻ Done")

            # Remove wav since we are done with it
            logger.info("♻ Removing wav version of %s", title)
            if wav_file_path.exists():
                wav_file_path.unlink()
            logger.info("♻ Done")

            if self.s3:
                self._upload_asset_s3(mp3_file_path, extension)
        else:
            logger.debug("Episode has already been converted: %s", mp3_file_path)

        if self.s3:
            # Convert mp3_file_path to a Path object and make relative to web_root
            s3_file_path = Path(mp3_file_path).relative_to(self.web_root)

            # Convert to posix path (forward slashes) for S3
            s3_key = s3_file_path.as_posix()

            msg = f"Checking length of s3 object: {s3_key}"
            logger.trace(msg)
            response = self.s3.head_object(Bucket=self.app_config.s3.bucket, Key=s3_key)
            new_length = response["ContentLength"]
            msg = f"Length of converted wav file {s3_key}: {new_length} bytes, stored in s3"
        else:
            new_length = mp3_file_path.stat().st_size
            msg = f"Length of converted wav file: {mp3_file_path} {new_length} bytes, stored locally"

        logger.trace(msg)

        return new_length

    def _upload_asset_s3(self, file_path: Path, extension: str, *, remove_original: bool = True) -> None:
        """Upload asset to s3."""
        if not self.s3:
            logger.error("⛅❌ s3 client not found, cannot upload")
            return
        content_type = CONTENT_TYPES[extension]
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = Path(self.web_root) / file_path
        s3_path = file_path.relative_to(self.web_root).as_posix()
        s3_path = s3_path.removeprefix("/")
        try:
            # Upload the file
            logger.info("💾⛅ Uploading to s3: %s", s3_path)
            self.s3.upload_file(
                str(file_path),
                self.app_config.s3.bucket,
                s3_path,
                ExtraArgs={"ContentType": content_type},
            )
            self.s3_paths_cache.append(s3_path)

            if remove_original:
                logger.info("💾 Removing local file: %s", file_path)
                try:
                    Path(file_path).unlink()
                except FileNotFoundError:  # Some weirdness when in debug mode, otherwise i'd use contextlib.suppress
                    msg = f"⛅❌ Could not remove the local file, the source file was not found: {file_path}"
                    logger.exception(msg)

        except FileNotFoundError:
            self.feed_download_healthy = False
            logger.exception("⛅❌ Could not upload to s3, the source file was not found: %s", file_path)
        except Exception:
            self.feed_download_healthy = False
            logger.exception("⛅❌ Unhandled s3 error: %s")

    async def _download_cover_art(self, url: str, title: str, podcast: PodcastConfig, extension: str = "") -> None:
        """Download cover art from url with appropriate file name."""
        content_dir = Path(self.web_root) / "content" / podcast.name_one_word
        cover_art_destination = content_dir / f"{title}{extension}"

        local_file_found = self._check_local_path_exists(cover_art_destination)

        if not local_file_found:
            await self._download_to_local(url, cover_art_destination)

        if self.s3:
            logger.info("💾⛅ Uploading podcast cover art to s3 not deleting local file to allow overriding")
            self._upload_asset_s3(cover_art_destination, extension, remove_original=False)

    async def _download_asset(
        self, url: str, title: str, podcast: PodcastConfig, extension: str = "", file_date_string: str = ""
    ) -> None:
        """Download asset from url with appropriate file name."""
        spacer = ""
        if file_date_string != "":
            spacer = "-"

        content_dir = Path(self.web_root) / "content" / podcast.name_one_word
        file_path = content_dir / f"{file_date_string}{spacer}{title}{extension}"

        if not self._check_path_exists(file_path):  # if the asset hasn't already been downloaded
            await self._download_to_local(url, file_path)
            logger.debug("Downloaded asset: %s", file_path)

            # For if we are using s3 as a backend
            # wav logic since this gets called in handle_wav
            if extension != ".wav" and self.s3:
                self._upload_asset_s3(file_path, extension)

        else:
            logger.trace(f"Already downloaded: {title}{extension}")

    async def _download_to_local(self, url: str, file_path: Path) -> None:
        """Download the asset from the url."""
        session = self._get_session()

        logger.debug("💾 Downloading: %s", url)
        logger.info("💾 Downloading asset to: %s", file_path)
        headers = {"user-agent": "Mozilla/5.0"}
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with file_path.open("wb") as asset_file:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        asset_file.write(chunk)

        except aiohttp.ServerTimeoutError:
            self.feed_download_healthy = False
            logger.exception("💾❌ Timeout Error: %s", url)
            return
        except aiohttp.ClientError:
            self.feed_download_healthy = False
            logger.exception("💾❌ Request Error: %s", url)
            return

        logger.debug("💾 Success!")

        if not self.s3:
            self._append_to_local_paths_cache(file_path)

    def _append_to_local_paths_cache(self, file_path: Path) -> None:
        file_path = Path(file_path).relative_to(self.web_root)

        if file_path not in self.local_paths_cache:
            self.local_paths_cache.append(file_path)

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

        logger.trace("Clean Filename: '%s'", file_name)
        return file_name
