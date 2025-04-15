import argparse
import logging

import pytest


def test_archivepodcast_cli_from__main__(tmp_path, monkeypatch, place_test_config, caplog):
    """TEST: Run CLI from main."""
    place_test_config("testing_true_valid.toml", tmp_path)

    from archivepodcast import __main__

    mock_args = argparse.Namespace(
        instance_path=str(tmp_path),
        config=str(tmp_path / "config.toml"),
    )
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    with caplog.at_level(logging.DEBUG):
        __main__.main()

    # We get to the intro
    assert "ArchivePodcast Version" in caplog.text
    assert " running adhoc" in caplog.text
    assert "ArchivePodcast ran adhoc in" in caplog.text


def test_archivepodcast_cli_from__main__no_provided_instance_path(tmp_path, monkeypatch, place_test_config, caplog):
    """TEST: Run CLI from main."""
    place_test_config("testing_true_valid.toml", tmp_path)

    from archivepodcast import __main__

    monkeypatch.setattr(
        "archivepodcast.__main__.INSTANCE_PATH",
        tmp_path,
    )  # Avoid pytest from using the repo's instance path

    mock_args = argparse.Namespace(
        instance_path="",
        config=str(tmp_path / "config.toml"),
    )
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    with caplog.at_level(logging.WARNING):
        __main__.main()

    # We get to the intro
    assert "Instance path not provided, using default" in caplog.text
    assert "not creating it for safety" not in caplog.text


def test_archivepodcast_cli_from__main__no_instance_path(tmp_path, monkeypatch, place_test_config, caplog):
    place_test_config("testing_true_valid.toml", tmp_path)

    from archivepodcast import __main__

    monkeypatch.setattr("pathlib.Path.exists", lambda x: False)  # Avoid pytest from using the repo's instance path

    monkeypatch.setattr(
        "archivepodcast.__main__.INSTANCE_PATH",
        tmp_path,
    )  # Avoid pytest from using the repo's instance path

    mock_args = argparse.Namespace(
        instance_path="",
        config=str(tmp_path / "config.toml"),
    )
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", lambda self: mock_args)

    with pytest.raises(FileNotFoundError):
        __main__.main()
