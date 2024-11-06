"""Set of functions to download podcasts to a directory"""
# and return xml that can be served to download them

import contextlib
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from http import HTTPStatus
from shutil import which  # shockingly this works on windows
from typing import TYPE_CHECKING
from urllib.error import HTTPError

import requests
from botocore.exceptions import (
    ClientError,
)  # No need to import boto3 since the object just gets passed in

from .logger import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

logger = get_logger(__name__)

IMAGE_FORMATS = [".webp", ".png", ".jpg", ".jpeg", ".gif"]
AUDIO_FORMATS = [".mp3", ".wav", ".m4a", ".flac"]

content_types = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mpeg",
    ".flac": "audio/flac",
}


PYDUB_LOADED = False
if which("ffmpeg") is not None:
    logger.trace("Trying to load pydub w/ffmpeg")
    try:
        from pydub import AudioSegment

        PYDUB_LOADED = True
    except ImportError:
        pass

else:
    logger.warning("❗ Not loading pydub since ffmpeg is not installed on this system (and in the PATH)")


class PodcastDownloader:
    """PodcastDownloader object."""

    def __init__(self, app_settings: dict, s3: S3Client, web_root: str) -> None:
        """Initialise the PodcastDownloader object."""
        self.reload_settings(app_settings, s3, web_root)

    def reload_settings(self, app_settings: dict, s3: S3Client, web_root: str) -> None:
        """Load/Reload settings of the app."""
        self.s3 = s3
        self.s3_paths_cache: list = []
        self.app_settings = app_settings
        self.web_root = web_root

    def download_podcast(self, podcast: dict) -> ET.ElementTree | None:
        """Parse the XML, Download all the assets, this is main."""
        response = None

        # lets fetch the original podcast xml
        request = podcast["url"]

        logger.debug(f"Downloading podcast rss: {request}")
        try:
            response = requests.get(request, timeout=5)
        except ValueError:  # NameResolutionError ?
            logger.exception("❌ Real early failure on grabbing the podcast xml, weird")
            return None

        if response is not None:
            if response.status_code != HTTPStatus.OK:
                logger.error("❌ Not a great web request, we got: %s", str(response.status_code))
                return None
            logger.debug(f"Good response {response.status_code}")
        else:
            logger.error("❌ Failure, no sign of a response.")
            logger.error("Probably an issue with the code. Or cloudflare ruining our day maybe?")
            return None

        # We have the xml
        podcast_xml = ET.fromstring(response.content)
        logger.info("📄 Downloaded RSS XML, Processing")
        logger.trace(str(podcast_xml))

        xml_first_child = podcast_xml[0]

        # It's time to iterate, we overwrite as necessary from the settings in settings.json
        title = ""
        url: str | None = ""

        for channel in xml_first_child:  # Dont complain
            logger.trace("Found XML item")
            logger.trace("XML tag: %s", channel.tag)

            # Handle URL, override
            if channel.tag == "link":
                logger.trace("Podcast link: %s", str(channel.text))
                channel.text = self.app_settings["inet_path"]

            # Handle Podcast Title, override
            elif channel.tag == "title":
                logger.info("📄 Podcast title: %s", str(channel.text))
                if podcast["new_name"] == "":
                    podcast["new_name"] = channel.text
                channel.text = podcast["new_name"]

            # Handle Podcast Description, override
            elif channel.tag == "description":
                logger.trace("Podcast description: %s", str(channel.text))
                channel.text = podcast["description"]

            # Remake Atom Tags
            elif channel.tag == "{http://www.w3.org/2005/Atom}link":
                channel.attrib["href"] = self.app_settings["inet_path"] + "rss/" + podcast["name_one_word"]
                channel.text = " "  # here me out...

            # Remake Apple Tags
            elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}owner":
                for child in channel:
                    if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}name":
                        if podcast["new_name"] == "":
                            podcast["new_name"] = child.text
                        child.text = podcast["new_name"]
                    if child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}email":
                        if podcast["contact_email"] == "":
                            podcast["contact_email"] = child.text
                        child.text = podcast["contact_email"]

            elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}author":
                if podcast["new_name"] == "":
                    podcast["new_name"] = channel.text
                channel.text = podcast["new_name"]

            elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}new-feed-url":
                channel.text = self.app_settings["inet_path"] + "rss/" + podcast["name_one_word"]

            elif channel.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
                if podcast["new_name"] == "":
                    podcast["new_name"] = channel.text
                title = podcast["new_name"]
                title = self._cleanup_file_name(title)
                url = channel.attrib.get("href")
                if url is None:
                    url = ""

                logger.trace("Image URL: %s", url)
                for filetype in IMAGE_FORMATS:
                    if filetype in url:
                        self._download_asset(url, title, podcast, filetype)
                        channel.attrib["href"] = (
                            self.app_settings["inet_path"]
                            + "content/"
                            + podcast["name_one_word"]
                            + "/"
                            + title
                            + filetype
                        )

                channel.text = " "

            # Handle Image
            elif channel.tag == "image":
                for child in channel:
                    logger.trace("image > XML tag: %s", child.tag)
                    if child.tag == "title":
                        logger.trace("Title: %s", str(child.text))
                        child.text = podcast["new_name"]

                    elif child.tag == "link":
                        child.text = self.app_settings["inet_path"]

                    elif child.tag == "url":
                        title = podcast["new_name"]
                        title = self._cleanup_file_name(title)
                        url = child.text
                        # Default to prevent unchanged url on error
                        child.text = ""
                        if url is None:
                            url = ""

                        for filetype in IMAGE_FORMATS:
                            if filetype in url:
                                self._download_asset(url, title, podcast, filetype)
                                child.text = (
                                    self.app_settings["inet_path"]
                                    + "content/"
                                    + podcast["name_one_word"]
                                    + "/"
                                    + title
                                    + filetype
                                )

                    else:
                        logger.trace(
                            "Unhandled XML tag %s, (under child.tag) leaving as-is",
                            child.tag,
                        )

                channel.text = " "  # here me out...

            # Handle Episode
            elif channel.tag == "item":
                file_date_string = "00000000"

                # Episode Date, need to do this before dealing with real data
                for child in channel:
                    if child.tag == "pubDate":
                        original_date = str(child.text)
                        file_date = datetime(1970, 1, 1)
                        with contextlib.suppress(ValueError):
                            file_date = datetime.strptime(original_date, "%a, %d %b %Y %H:%M:%S %Z")
                        with contextlib.suppress(ValueError):
                            file_date = datetime.strptime(original_date, "%a, %d %b %Y %H:%M:%S %z")
                        file_date_string = file_date.strftime("%Y%m%d")

                for child in channel:
                    logger.trace("item > XML tag: %s", child.tag)
                    # Episode Title
                    if child.tag == "title":
                        title = str(child.text)
                        logger.trace("Title: %s", title)

                    # Episode Content (Enclosure)
                    elif child.tag == "enclosure" or "{http://search.yahoo.com/mrss/}content" in child.tag:
                        title = self._cleanup_file_name(title)
                        url = child.attrib.get("url")
                        # Default to prevent unchanged url on error
                        child.attrib["url"] = ""
                        if url is None:
                            url = ""
                        for audio_format in AUDIO_FORMATS:
                            new_audio_format = audio_format
                            if audio_format in url:
                                if audio_format == ".wav":
                                    # Download the wav, and get the new length of the file for the xml
                                    new_length = self._handle_wav(
                                        url,
                                        title,
                                        podcast,
                                        audio_format,
                                        file_date_string,
                                    )
                                    new_audio_format = ".mp3"
                                    child.attrib["type"] = "audio/mpeg"
                                    # Recalculate file size for the xml
                                    child.attrib["length"] = str(new_length)

                                else:
                                    self._download_asset(
                                        url,
                                        title,
                                        podcast,
                                        audio_format,
                                        file_date_string,
                                    )
                                # Set path of audio file
                                child.attrib["url"] = (
                                    self.app_settings["inet_path"]
                                    + "content/"
                                    + podcast["name_one_word"]
                                    + "/"
                                    + file_date_string
                                    + "-"
                                    + title
                                    + new_audio_format
                                )

                    # Episode Image
                    elif child.tag == "{http://www.itunes.com/dtds/podcast-1.0.dtd}image":
                        title = self._cleanup_file_name(title)
                        url = child.attrib.get("href")
                        if url is None:
                            url = ""
                        for filetype in IMAGE_FORMATS:
                            if filetype in url:
                                self._download_asset(
                                    url,
                                    title,
                                    podcast,
                                    filetype,
                                    file_date_string,
                                )
                                # Set path of image
                                child.attrib["href"] = (
                                    self.app_settings["inet_path"]
                                    + "content/"
                                    + podcast["name_one_word"]
                                    + "/"
                                    + file_date_string
                                    + "-"
                                    + title
                                    + filetype
                                )

                    else:
                        logger.trace(
                            "Unhandled XML tag %s, (under child.tag) leaving as-is",
                            child.tag,
                        )

            else:
                logger.trace("Unhandled XML tag %s, (under channel.tag) leaving as-is", channel.tag)

        podcast_xml[0] = xml_first_child

        tree = ET.ElementTree(podcast_xml)
        # These make the name spaces appear nicer in the generated XML
        ET.register_namespace("googleplay", "http://www.google.com/schemas/play-podcasts/1.0")
        ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
        ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        ET.register_namespace("media", "http://search.yahoo.com/mrss/")
        ET.register_namespace("sy", "http://purl.org/rss/1.0/modules/syndication/")
        ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
        ET.register_namespace("wfw", "http://wellformedweb.org/CommentAPI/")
        ET.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
        ET.register_namespace("slash", "http://purl.org/rss/1.0/modules/slash/")
        ET.register_namespace("rawvoice", "http://www.rawvoice.com/rawvoiceRssModule/")
        ET.register_namespace("spotify", "http://www.spotify.com/ns/rss/")
        ET.register_namespace("feedburner", "http://rssnamespace.org/feedburner/ext/1.0")

        return tree

    def _check_local_path_exists(self, file_path: str) -> bool:
        """Check if the file exists locally."""
        return os.path.isfile(file_path)

    def _check_path_exists(self, file_path: str) -> bool:
        """Check the path, s3 or local."""
        file_exists = False

        if self.s3 is not None:
            s3_file_path = file_path.replace(self.web_root, "").replace(os.sep, "/")
            if s3_file_path[0] == "/":
                s3_file_path = s3_file_path[1:]

            if s3_file_path not in self.s3_paths_cache:
                try:
                    # Head object to check if file exists
                    self.s3.head_object(Bucket=self.app_settings["s3"]["bucket"], Key=s3_file_path)
                    logger.debug(
                        "⛅ File: %s exists in s3 bucket",
                        s3_file_path,
                    )
                    self.s3_paths_cache.append(s3_file_path)
                    file_exists = True

                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        logger.debug(
                            "File %s does not exist 🙅‍ in the s3 bucket %s",
                            s3_file_path,
                            self.app_settings["s3"]["bucket"],
                        )
                    else:
                        logger.exception("⛅❌ s3 check file exists errored out?")
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception("⛅❌ Unhandled s3 Error:")

            else:
                logger.trace("s3 path %s exists in s3_paths_cache, skipping", s3_file_path)
                file_exists = True

        else:
            file_exists = self._check_local_path_exists(file_path)

        return file_exists

    def _handle_wav(self, url: str, title: str, podcast: dict, extension: str = "", file_date_string: str = "") -> int:
        """Convert podcasts that have wav episodes 😔. Returns new file length."""
        new_length = None
        spacer = ""  # This logic can be removed since WAVs will always have a date
        if file_date_string != "":
            spacer = "-"
        wav_file_path = os.path.join(
            self.web_root,
            "content",
            podcast["name_one_word"],
            f"{file_date_string}{spacer}{title}.wav",
        )

        mp3_file_path = os.path.join(
            self.web_root,
            "content",
            podcast["name_one_word"],
            f"{file_date_string}{spacer}{title}.mp3",
        )

        # If we need do download and convert a wav there is a small chance
        # the user has had ffmpeg issues, remove existing files to play it safe
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)
            os.remove(mp3_file_path)

        # If the asset hasn't already been downloaded and converted
        if not self._check_path_exists(mp3_file_path):
            if PYDUB_LOADED:
                self._download_asset(
                    url,
                    title,
                    podcast,
                    extension,
                    file_date_string,
                )

                logger.info("♻ Converting episode %s to mp3", title)
                sound = AudioSegment.from_wav(wav_file_path)
                sound.export(mp3_file_path, format="mp3")
                logger.info("♻ Done")

                # Remove wav since we are done with it
                logger.info("♻ Removing wav version of %s", title)
                if os.path.exists(wav_file_path):
                    os.remove(wav_file_path)
                logger.info("♻ Done")

                self._upload_asset_s3(mp3_file_path, extension, file_date_string)

            else:
                if not PYDUB_LOADED:
                    logger.error("❌ pydub pip package not installed")

                logger.error("❌ Cannot convert wav to mp3!")

        if self.app_settings["storage_backend"] == "s3":
            s3_file_path = mp3_file_path.replace(self.web_root, "")
            msg = f"Checking length of s3 object: { s3_file_path }"
            logger.trace(msg)
            response = self.s3.head_object(Bucket=self.app_settings["s3"]["bucket"], Key=s3_file_path)
            new_length = response["ContentLength"]
            msg = f"Length of converted wav file { s3_file_path }: { new_length }"
        else:
            new_length = os.stat(mp3_file_path).st_size
            msg = f"Length of converted wav file { mp3_file_path }: { new_length }"

        logger.trace(msg)

        return new_length

    def _upload_asset_s3(self, file_path: str, extension: str, file_date_string: str) -> None:
        """Upload asset to s3."""
        content_type = content_types[extension]
        s3_path = file_path.replace(self.web_root, "")
        if s3_path[0] == "/":  # TODO: Check if needed
            s3_path = s3_path[1:]
        try:
            # Upload the file
            logger.info("💾⛅ Uploading to s3: %s", s3_path)
            self.s3.upload_file(
                file_path,
                self.app_settings["s3"]["bucket"],
                s3_path,
                ExtraArgs={"ContentType": content_type},
            )
            if file_date_string == "":  # This means that the cover image is never removed from the filesystem
                logger.info(
                    "💾⛅ s3 upload successful, not removing podcast cover art from filesystem "
                    "(this is intended for overriding)"
                )
            else:
                logger.info("💾⛅ s3 upload successful, removing local file")
                os.remove(file_path)
        except FileNotFoundError:
            logger.exception("⛅❌ Could not upload to s3, the source file was not found: %s", file_path)
        except Exception:
            logger.exception("⛅❌ Unhandled s3 Error: %s")

    def _download_asset(
        self, url: str, title: str, podcast: dict, extension: str = "", file_date_string: str = ""
    ) -> None:
        """Download asset from url with appropriate file name."""
        spacer = ""
        if file_date_string != "":
            spacer = "-"

        file_path = os.path.join(
            self.web_root, "content", podcast["name_one_word"], f"{file_date_string}{spacer}{title}{extension}"
        )

        if not self._check_path_exists(file_path):  # if the asset hasn't already been downloaded
            if not self._check_local_path_exists(file_path):  # logic to upload replacement art if needed
                try:
                    logger.debug("Downloading: %s", url)
                    logger.info("💾 Downloading asset to: %s", file_path)
                    headers = {"user-agent": "Mozilla/5.0"}
                    req = requests.get(url, headers=headers, timeout=5)

                    if req.status_code == HTTPStatus.OK:
                        with open(file_path, "wb") as asset_file:
                            asset_file.write(req.content)
                            logger.info("💾 Success!")
                    else:
                        logger.error("💾❌ HTTP ERROR: %s", str(req.content))

                except HTTPError:
                    logger.exception("💾❌ Download Failed")

            # For if we are using s3 as a backend
            # wav logic since this gets called in handle_wav
            if extension != ".wav" and self.app_settings["storage_backend"] == "s3":
                self._upload_asset_s3(file_path, extension, file_date_string)

        else:
            logger.trace(f"Already downloaded: {title}{extension}")

    def _cleanup_file_name(self, file_name: str | bytes) -> str:
        """Standardise naming, generate a slug."""
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
