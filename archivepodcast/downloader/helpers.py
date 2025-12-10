"""Helpers for downloader module."""

import asyncio
import random
import shutil
import sys
from pathlib import Path

import ffmpeg

from archivepodcast.constants import AP_SELF_TEST
from archivepodcast.utils.logger import get_logger

from .constants import FFMPEG_INFO

logger = get_logger(__name__)


async def delay_download(attempt: int) -> None:
    """Sleep for an exponential backoff period based on the attempt number."""
    await asyncio.sleep(random.uniform(0.1, 1) + (0.5 * attempt))


def convert_to_mp3(input_path: Path, output_path: Path) -> None:
    """Convert an audio file to MP3 using ffmpeg."""
    ff_input = ffmpeg.input(filename=input_path)
    ff = ffmpeg.output(ff_input, filename=output_path, codec="libmp3lame", aq=4)
    ff.run(overwrite_output=True)


def _ffmpeg_convert_check() -> None:
    test_wav_bytes = (
        bytes.fromhex("524946469822000057415645666D7420100000000100010044AC000088580100020010006461746174220000")
        + b"\x00" * 5120
    )
    wav_path = Path("/tmp/test.wav")  # noqa: S108

    if wav_path.exists():
        wav_path.unlink()

    wav_path.write_bytes(test_wav_bytes)

    mp3_path = wav_path.with_suffix(".mp3")
    logger.info("Performing ffmpeg conversion check")
    convert_to_mp3(input_path=wav_path, output_path=mp3_path)


def check_ffmpeg(*, convert_check: bool = False) -> None:
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

    if AP_SELF_TEST or convert_check:
        _ffmpeg_convert_check()


check_ffmpeg()
