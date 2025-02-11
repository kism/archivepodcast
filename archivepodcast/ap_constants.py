"""Constants for ArchivePodcast."""

import datetime

import psutil

# Test FFMPEG
FFMPEG_INFO = """ffmpeg not found, please install it and ensure it's in PATH.
https://www.ffmpeg.org/download.html
 apt install ffmpeg
 brew install ffmpeg
 scoop install ffmpeg
exiting..."""

IMAGE_FORMATS = [".webp", ".png", ".jpg", ".jpeg", ".gif"]
AUDIO_FORMATS = [".mp3", ".wav", ".m4a", ".flac"]
CONTENT_TYPES = {
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

TZINFO_UTC = datetime.datetime.now(datetime.UTC).astimezone().tzinfo

PODCAST_DATE_FORMATS = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"]

PROCESS = psutil.Process()
