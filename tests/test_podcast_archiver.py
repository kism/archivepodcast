"""App testing different config behaviours."""

import logging
import os


def test_no_about_page(pa, caplog):
    """Test no about page."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        pa.make_about_page()

    assert "About page doesn't exist" in caplog.text


def test_about_page(pa, caplog, tmp_path):
    """Test about page."""
    with open(os.path.join(tmp_path, "web", "about.html"), "w") as f:
        f.write("About page exists!")

    with caplog.at_level(level=logging.INFO, logger="archivepodcast.ap_archiver"):
        pa.make_about_page()

    assert "About page exists!" in caplog.text


def test_check_s3_files(pa, caplog):
    """Test that s3 files are checked."""
    with caplog.at_level(level=logging.DEBUG, logger="archivepodcast.ap_archiver"):
        pa.check_s3_files()

    assert "Checking state of s3 bucket" in caplog.text
    assert "No s3 client to list" in caplog.text
