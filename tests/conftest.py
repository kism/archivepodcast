"""The conftest.py file serves as a means of providing fixtures for an entire directory.

Fixtures defined in a conftest.py can be used by any test in that package without needing to import them.
"""

import os

import pytest

from archivepodcast.logger import TRACE_LEVEL_NUM

FLASK_ROOT_PATH = os.getcwd()
TEST_CONFIGS_LOCATION = os.path.join(os.getcwd(), "tests", "configs")
TEST_RSS_LOCATION = os.path.join(os.getcwd(), "tests", "rss")

# Test WAV File
# This is easier than: ffmpeg.input("anullsrc", f="lavfi", t=10).output(filename=tmp_wav_path, codec="pcm_s16le").run()
microsoft_wav_header = bytes.fromhex(
    "524946469822000057415645666D7420100000000100010044AC000088580100020010006461746174220000"
)
null_audio_data = b"\x00" * 5120
TEST_WAV_FILE = microsoft_wav_header + null_audio_data


DUMMY_RSS_STR = "<?xml version='1.0' encoding='utf-8'?>\n<rss><item>Dummy RSS</item></rss>"


def pytest_configure():
    """Magic function to set module level variables."""
    pytest.TEST_CONFIGS_LOCATION = TEST_CONFIGS_LOCATION
    pytest.TEST_WAV_FILE = TEST_WAV_FILE
    pytest.DUMMY_RSS_STR = DUMMY_RSS_STR
    pytest.TEST_RSS_LOCATION = TEST_RSS_LOCATION
    pytest.TRACE_LEVEL_NUM = TRACE_LEVEL_NUM
    pytest.FLASK_ROOT_PATH = FLASK_ROOT_PATH


pytest_plugins = [ # Magic list of fixtures to load
    "tests.fixtures.archivepodcast_app",
    "tests.fixtures.archivepodcast_obj",
    "tests.fixtures.aws",
    "tests.fixtures.configs",
    "tests.fixtures.requests",
    "tests.fixtures.threading",
]
