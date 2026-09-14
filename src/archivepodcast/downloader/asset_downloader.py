"""Actually Download Assets."""

import contextlib
import time
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
from anyio import Path as AsyncPath
from botocore.exceptions import ClientError as S3ClientError

from archivepodcast.instances.path_cache import local_file_cache, s3_file_cache
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.utils.log_messages import log_aiohttp_exception
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.s3 import S3File, s3_head, s3_put
from archivepodcast.utils.time import warn_if_too_long

from .constants import CONTENT_TYPES, DOWNLOAD_RETRY_COUNT
from .helpers import convert_to_mp3, delay_download

if TYPE_CHECKING:
    from archivepodcast.config import AppConfig, PodcastConfig

logger = get_logger(__name__)


def _append_to_local_paths_cache(file_path: Path) -> None:
    local_file_cache.add_file(file_path.relative_to(get_app_paths().web_root))


def _check_local_path_exists(file_path: Path) -> bool:
    """Check if the file exists locally."""
    file_exists = file_path.is_file()

    if file_exists:
        _append_to_local_paths_cache(file_path)
        logger.trace("File: %s exists locally", file_path)
    else:
        logger.trace("File: %s does not exist locally", file_path)

    return file_exists


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
        file_name = f"{file_date_string}-{title}" if file_date_string else title
        file_path = get_app_paths().web_root / "content" / self._podcast.name_one_word / f"{file_name}{extension}"

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

        for n in range(DOWNLOAD_RETRY_COUNT):
            start_time = time.time()
            try:
                async with self._aiohttp_session.get(url) as response:
                    response.raise_for_status()
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with file_path.open("wb") as asset_file:
                        async for chunk in response.content.iter_chunked(8192):
                            asset_file.write(chunk)
            except aiohttp.ClientError as e:
                self._feed_download_healthy = False
                log_aiohttp_exception(self._podcast.name_one_word, url, e, logger)
                await delay_download(n)
                continue
            warn_if_too_long(f"download asset: {file_path}", time.time() - start_time, large_file=True)
            break
        else:
            logger.error("[%s] Failed to download asset after multiple attempts: %s", self._podcast.name_one_word, url)
            return

        logger.info("[%s] Downloaded asset to: %s", self._podcast.name_one_word, file_path)

        if not self._s3:
            _append_to_local_paths_cache(file_path)

    async def _download_cover_art(self, url: str, title: str, extension: str = "") -> None:
        """Download cover art, the local copy is kept even with s3 since it is small."""
        cover_art_destination = (
            get_app_paths().web_root / "content" / self._podcast.name_one_word / f"{title}{extension}"
        )
        local_file_found = _check_local_path_exists(cover_art_destination)

        if not local_file_found and self._s3 and await self._check_path_exists(cover_art_destination):
            return  # Already in s3, nothing to do
        if not local_file_found:
            await self._download_to_local(url, cover_art_destination)
        if self._s3:
            await self._upload_asset_s3(cover_art_destination, extension, remove_original=False)

    async def _handle_wav(self, url: str, title: str, extension: str, file_date_string: str) -> int:
        """Convert podcasts that have wav episodes 😔. Returns new file length."""
        logger.trace("[%s] Handling wav file: %s", self._podcast.name_one_word, title)
        content_dir = get_app_paths().web_root / "content" / self._podcast.name_one_word
        wav_file_path: AsyncPath = AsyncPath(content_dir / f"{file_date_string}-{title}.wav")
        mp3_file_path: AsyncPath = AsyncPath(content_dir / f"{file_date_string}-{title}.mp3")

        # If we need do download and convert a wav there is a small chance
        # the user has had ffmpeg issues, remove existing files to play it safe
        if await wav_file_path.exists():
            with contextlib.suppress(Exception):
                await wav_file_path.unlink()
                await mp3_file_path.unlink()

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
            if await wav_file_path.exists():
                await wav_file_path.unlink()
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

            response = await s3_head(self._app_config.s3.bucket, s3_key)
            new_length = response["ContentLength"]
            msg = f"Length of converted wav file {s3_key}: {new_length} bytes, stored in s3"
        else:
            new_length = (await mp3_file_path.stat()).st_size
            msg = f"Length of converted wav file: {mp3_file_path} {new_length} bytes, stored locally"

        logger.trace("[%s] %s", self._podcast.name_one_word, msg)

        return new_length

    # region S3 Upload

    async def _upload_asset_s3(
        self, file_path: Path | AsyncPath, extension: str, *, remove_original: bool = True
    ) -> None:
        """Upload asset to s3."""
        content_type = CONTENT_TYPES[extension]
        file_path = Path(file_path)
        s3_path = file_path.relative_to(get_app_paths().web_root).as_posix()

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
            await self._put_asset_s3(file_path, s3_path, content_type, remove_original=remove_original)
        except FileNotFoundError:
            self._feed_download_healthy = False
            logger.exception(
                "[%s] Could not upload to s3, the source file was not found: %s", self._podcast.name_one_word, file_path
            )
        except Exception:
            self._feed_download_healthy = False
            logger.exception("[%s] Unhandled s3 error: %s", self._podcast.name_one_word, file_path)

    async def _put_asset_s3(self, file_path: Path, s3_path: str, content_type: str, *, remove_original: bool) -> None:
        """Upload the file to s3, cache it, and optionally remove the local copy."""
        if remove_original:
            logger.info("[%s] Uploading to s3: %s", self._podcast.name_one_word, s3_path)
        else:
            logger.debug("[%s] Uploading to s3: %s", self._podcast.name_one_word, s3_path)

        body = await AsyncPath(file_path).read_bytes()
        await s3_put(self._app_config.s3.bucket, s3_path, body, content_type, large_file=True)
        logger.trace("[%s] Uploaded asset to s3: %s", self._podcast.name_one_word, s3_path)

        s3_file_cache.add_file(S3File(key=s3_path, size=len(body)))

        if remove_original:
            logger.info("[%s] Removing local file: %s", self._podcast.name_one_word, file_path)
            try:
                await AsyncPath(file_path).unlink()
            except FileNotFoundError:  # Some weirdness when in debug mode, otherwise i'd use contextlib.suppress
                msg = f"Could not remove the local file, the source file was not found: {file_path}"
                logger.exception("[%s] %s", self._podcast.name_one_word, msg)

    # region Helpers

    async def _check_path_exists(self, file_path: Path | AsyncPath) -> bool:
        """Check the path (absolute, under web_root), s3 or local."""
        file_path = Path(file_path)
        if not self._s3:
            return _check_local_path_exists(file_path)

        s3_key = file_path.relative_to(get_app_paths().web_root).as_posix()
        if s3_file_cache.check_file_exists(s3_key):
            logger.trace("s3 path %s exists in s3_paths_cache, skipping", s3_key)
            return True

        try:
            my_object = await s3_head(self._app_config.s3.bucket, s3_key)
        except S3ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                logger.debug("File: %s does not exist 🙅‍ in the s3 bucket", s3_key)
            else:
                logger.exception("s3 check file exists errored out?")
            return False
        except Exception:
            logger.exception("Unhandled s3 Error:")
            return False

        logger.debug("File: %s exists in s3 bucket", s3_key)
        s3_file_cache.add_file(S3File(key=s3_key, size=my_object.get("ContentLength", 0)))
        return True
