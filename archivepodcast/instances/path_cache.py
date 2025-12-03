"""Path cache for S3 files."""

from archivepodcast.utils.file_cache import LocalFileCache
from archivepodcast.utils.s3 import S3FileCache

s3_file_cache = S3FileCache()
local_file_cache = LocalFileCache()
