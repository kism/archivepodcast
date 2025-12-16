from pathlib import Path

FLASK_ROOT_PATH = Path.cwd()
TEST_CONFIGS_LOCATION = FLASK_ROOT_PATH / "tests" / "configs"
TEST_RSS_LOCATION = FLASK_ROOT_PATH / "tests" / "rss"

# Test WAV File
# This is easier than: ffmpeg.input("anullsrc", f="lavfi", t=10).output(filename=tmp_wav_path, codec="pcm_s16le").run()
microsoft_wav_header = bytes.fromhex(
    "524946469822000057415645666D7420100000000100010044AC000088580100020010006461746174220000"
)
null_audio_data = b"\x00" * 5120
TEST_WAV_FILE = microsoft_wav_header + null_audio_data


DUMMY_RSS_STR = "<?xml version='1.0' encoding='UTF-8'?>\n<rss version=\"2.0\"><channel><title>Test</title><item><title>Dummy RSS</title></item></channel></rss>"
