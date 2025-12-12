"""Actually Download Assets."""

import contextlib
import time
from pathlib import Path

import aiohttp
from aiobotocore.session import get_session
from botocore.exceptions import ClientError as S3ClientError

from archivepodcast.config import AppConfig, PodcastConfig
from archivepodcast.instances.config import get_ap_config_s3_client
from archivepodcast.instances.path_cache import local_file_cache, s3_file_cache
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.utils.log_messages import log_aiohttp_exception
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.s3 import S3File
from archivepodcast.utils.time import warn_if_too_long

from .constants import CONTENT_TYPES, DOWNLOAD_RETRY_COUNT
from .helpers import convert_to_mp3, delay_download

logger = get_logger(__name__)


class AssetDownloader:
    """Asset Downloader object."""

    def __init__(
        self,
        podcast: PodcastConfig,
        app_config: AppConfig,
        *,
        s3: bool,
        aiohttp_session: aiohttp.ClientSession,
    ) -> None:
        """Initialise the AssetDownloader object."""
        logger.trace("Initialising AssetDownloader for podcast: %s", podcast.name_one_word)
        self._podcast = podcast
        self._app_config = app_config
        self._s3 = s3
        self._aiohttp_session = aiohttp_session
        self._feed_download_healthy: bool = True
        self._rss_file_path = get_app_paths().web_root / "rss" / podcast.name_one_word

    # region Download Methods

    async def _download_asset(self, url: str, title: str, extension: str = "", file_date_string: str = "") -> None:
        """Download asset from url with appropriate file name."""
        spacer = ""
        if file_date_string != "":
            spacer = "-"

        content_dir = get_app_paths().web_root / "content" / self._podcast.name_one_word
        file_path = content_dir / f"{file_date_string}{spacer}{title}{extension}"

        if not await self._check_path_exists(file_path):  # if the asset hasn't already been downloaded
            await self._download_to_local(url, file_path)
            logger.debug("Downloaded asset: %s", file_path)

            # For if we are using s3 as a backend
            # wav logic since this gets called in handle_wav
            if extension != ".wav" and self._s3:
                await self._upload_asset_s3(file_path, extension)

        else:
            logger.trace(f"Already downloaded: {title}{extension}")

    async def _download_to_local(self, url: str, file_path: Path) -> None:
        """Download the asset from the url."""
        logger.debug("[%s] Downloading: %s", self._podcast.name_one_word, url)

        async def _attempt_download() -> bool:
            """Attempt to download the asset."""
            try:
                logger.trace("[%s] Downloading asset from URL: %s", self._podcast.name_one_word, url)
                start_time = time.time()
                async with self._aiohttp_session.get(url) as response:
                    response.raise_for_status()
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with file_path.open("wb") as asset_file:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            asset_file.write(chunk)

                warn_if_too_long(f"download asset: {file_path}", time.time() - start_time, large_file=True)

            except aiohttp.ClientError as e:
                self._feed_download_healthy = False
                log_aiohttp_exception(self._podcast.name_one_word, url, e, logger)
                return False

            logger.info("[%s] Downloaded asset to: %s", self._podcast.name_one_word, file_path)

            return True

        success = False
        for n in range(DOWNLOAD_RETRY_COUNT):
            success = await _attempt_download()
            if success:
                break
            await delay_download(n)
        if not success:
            logger.error("[%s] Failed to download asset after multiple attempts: %s", self._podcast.name_one_word, url)
            return

        logger.debug("[%s] Success, downloaded to %s", self._podcast.name_one_word, file_path)

        if not self._s3:
            self._append_to_local_paths_cache(file_path)

    async def _download_cover_art(
        self,
        url: str,
        title: str,
        extension: str = "",
    ) -> None:
        """Download cover art from url with appropriate file name."""
        content_dir = get_app_paths().web_root / "content" / self._podcast.name_one_word
        cover_art_destination = content_dir / f"{title}{extension}"

        remote_file_found = False
        local_file_found = self._check_local_path_exists(cover_art_destination)

        # If we are using s3
        #    we haven't found the local file
        #    we will remove the original after upload
        # Check s3 for the file
        if self._s3 and not local_file_found and await self._check_path_exists(cover_art_destination):
            remote_file_found = True

        logger.trace(
            "[%s] _download_cover_art, local_file_found=%s, remote_file_found=%s",
            self._podcast.name_one_word,
            local_file_found,
            remote_file_found,
        )

        # Download to local if we aren't using s3 and haven't found it locally
        if not self._s3 and not local_file_found:
            await self._download_to_local(url, cover_art_destination)

        # Download to local if we haven't found it locally or remotely
        if self._s3 and not local_file_found and not remote_file_found:
            await self._download_to_local(url, cover_art_destination)

        # If we (now) have a file here, upload to s3 if needed
        if self._s3 and (local_file_found or not remote_file_found):
            await self._upload_asset_s3(cover_art_destination, extension, remove_original=False)

    async def _handle_wav(self, url: str, title: str, extension: str = "", file_date_string: str = "") -> int:
        """Convert podcasts that have wav episodes 😔. Returns new file length."""
        logger.trace("[%s] Handling wav file: %s", self._podcast.name_one_word, title)
        new_length = None
        spacer = ""  # This logic can be removed since WAVs will always have a date
        if file_date_string != "":
            spacer = "-"

        content_dir = get_app_paths().web_root / "content" / self._podcast.name_one_word
        wav_file_path: Path = content_dir / f"{file_date_string}{spacer}{title}.wav"
        mp3_file_path: Path = content_dir / f"{file_date_string}{spacer}{title}.mp3"

        # If we need do download and convert a wav there is a small chance
        # the user has had ffmpeg issues, remove existing files to play it safe
        if wav_file_path.exists():
            with contextlib.suppress(Exception):
                wav_file_path.unlink()
                mp3_file_path.unlink()

        # If the asset hasn't already been downloaded and converted
        if not await self._check_path_exists(mp3_file_path):
            await self._download_asset(
                url,
                title,
                extension,
                file_date_string,
            )

            logger.info("♻ Converting episode %s to mp3", title)
            logger.debug("♻ MP3 File Path: %s", mp3_file_path)

            convert_to_mp3(wav_file_path, mp3_file_path)

            logger.info("♻ Done")

            # Remove wav since we are done with it
            logger.info("♻ Removing wav version of %s", title)
            if wav_file_path.exists():
                wav_file_path.unlink()
            logger.info("♻ Done")

            if self._s3:
                await self._upload_asset_s3(mp3_file_path, extension)
        else:
            logger.debug("Episode has already been converted: %s", mp3_file_path)

        if self._s3:
            # Convert mp3_file_path to a Path object and make relative to web_root
            s3_file_path = Path(mp3_file_path).relative_to(get_app_paths().web_root)

            # Convert to posix path (forward slashes) for S3
            s3_key = s3_file_path.as_posix()

            msg = f"Checking length of s3 object: {s3_key}"
            logger.trace("[%s] %s", self._podcast.name_one_word, msg)

            session = get_session()
            ap_s3_config = get_ap_config_s3_client()
            async with session.create_client("s3", **ap_s3_config.__dict__) as s3_client:
                response = await s3_client.head_object(Bucket=self._app_config.s3.bucket, Key=s3_key)

            new_length = response["ContentLength"]
            msg = f"Length of converted wav file {s3_key}: {new_length} bytes, stored in s3"
        else:
            new_length = mp3_file_path.stat().st_size
            msg = f"Length of converted wav file: {mp3_file_path} {new_length} bytes, stored locally"

        logger.trace("[%s] %s", self._podcast.name_one_word, msg)

        return new_length

    # region S3 Upload

    async def _upload_asset_s3(self, file_path: Path, extension: str, *, remove_original: bool = True) -> None:
        """Upload asset to s3."""
        if not self._s3:
            logger.error("[%s] s3 client not found, cannot upload", self._podcast.name_one_word)
            return
        content_type = CONTENT_TYPES[extension]
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = get_app_paths().web_root / file_path
        s3_path = file_path.relative_to(get_app_paths().web_root).as_posix()
        s3_path = s3_path.removeprefix("/")

        if not remove_original:
            # So if we are not removing the original, we can check if we can skip the upload
            file_size = file_path.stat().st_size
            if s3_file_cache.check_file_exists(s3_path, file_size):
                logger.debug(
                    "[%s] File: %s exists in s3_paths_cache and matches in size, skipping upload",
                    self._podcast.name_one_word,
                    s3_path,
                )
                return

        try:
            # Upload the file
            session = get_session()
            ap_s3_config = get_ap_config_s3_client()
            async with session.create_client("s3", **ap_s3_config.__dict__) as s3_client:
                if remove_original:
                    logger.info("[%s] Uploading to s3: %s", self._podcast.name_one_word, s3_path)
                else:
                    logger.debug("[%s] Uploading to s3: %s", self._podcast.name_one_word, s3_path)

                start_time = time.time()
                await s3_client.put_object(
                    Bucket=self._app_config.s3.bucket,
                    Key=s3_path,
                    Body=file_path.read_bytes(),
                    ContentType=content_type,
                )
                warn_if_too_long(
                    f"[{self._podcast.name_one_word}] upload asset to s3: {s3_path}",
                    time.time() - start_time,
                    large_file=True,
                )
                logger.trace("[%s] Uploaded asset to s3: %s", self._podcast.name_one_word, s3_path)

            s3_file_cache.add_file(S3File(key=s3_path, size=file_path.stat().st_size))

            if remove_original:
                logger.info("[%s] Removing local file: %s", self._podcast.name_one_word, file_path)
                try:
                    Path(file_path).unlink()
                except FileNotFoundError:  # Some weirdness when in debug mode, otherwise i'd use contextlib.suppress
                    msg = f"Could not remove the local file, the source file was not found: {file_path}"
                    logger.exception("[%s] %s", self._podcast.name_one_word, msg)

        except FileNotFoundError:
            self._feed_download_healthy = False
            logger.exception(
                "[%s] Could not upload to s3, the source file was not found: %s", self._podcast.name_one_word, file_path
            )
        except Exception:
            self._feed_download_healthy = False
            logger.exception("[%s] Unhandled s3 error: %s", self._podcast.name_one_word, file_path)

    # region Helpers

    def _check_local_path_exists(self, file_path: Path) -> bool:
        """Check if the file exists locally."""
        file_exists = file_path.is_file()

        if file_exists:
            self._append_to_local_paths_cache(file_path)
            logger.trace("File: %s exists locally", file_path)
        else:
            logger.trace("File: %s does not exist locally", file_path)

        return file_exists

    async def _check_path_exists(self, file_path: Path | str) -> bool:
        """Check the path, s3 or local."""
        file_exists = False

        if self._s3:
            # Convert file_path to a Path object if it isn't already
            file_path = Path(file_path)

            # If it's an absolute path and under web_root, make it relative to web_root
            if file_path.is_absolute() and file_path.is_relative_to(get_app_paths().web_root):
                file_path = file_path.relative_to(get_app_paths().web_root)

            # Convert to a posix path (forward slashes) and ensure no leading slash
            s3_key = file_path.as_posix().lstrip("/")

            if not s3_file_cache.check_file_exists(s3_key):
                session = get_session()
                ap_s3_config = get_ap_config_s3_client()

                async with session.create_client("s3", **ap_s3_config.__dict__) as s3_client:
                    try:
                        # Head object to check if file exists
                        my_object = await s3_client.head_object(Bucket=self._app_config.s3.bucket, Key=s3_key)
                        logger.debug(
                            "File: %s exists in s3 bucket",
                            s3_key,
                        )
                        s3_file_cache.add_file(S3File(key=s3_key, size=my_object.get("ContentLength", 0)))
                        file_exists = True

                    except S3ClientError as e:
                        if e.response.get("Error", {}).get("Code") == "404":
                            logger.debug(
                                "File: %s does not exist 🙅‍ in the s3 bucket",
                                s3_key,
                            )
                        else:
                            logger.exception("s3 check file exists errored out?")
                    except Exception:  # pylint: disable=broad-exception-caught
                        logger.exception("Unhandled s3 Error:")

            else:
                logger.trace("s3 path %s exists in s3_paths_cache, skipping", s3_key)
                file_exists = True

        else:
            if not isinstance(file_path, Path):
                file_path = Path(file_path)
            file_exists = self._check_local_path_exists(file_path)

        return file_exists

    def _append_to_local_paths_cache(self, file_path: Path) -> None:
        file_path = Path(file_path).relative_to(get_app_paths().web_root)

        if not local_file_cache.check_exists(file_path):
            local_file_cache.add_file(file_path)
