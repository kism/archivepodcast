"""Unit tests for configuration module."""

import pytest

import archivepodcast

DEFAULT_CONFIG = archivepodcast.config.DEFAULT_CONFIG


def test_config_permissions_error_read(place_test_config, tmp_path, mocker):
    """Verify permissions error is raised when config file cannot be read."""
    place_test_config("testing_true_valid.toml", tmp_path)

    mock_open_func = mocker.mock_open(read_data="")
    mock_open_func.side_effect = PermissionError("Permission denied")

    mocker.patch("pathlib.Path.open", mock_open_func)

    # TEST: PermissionsError is raised.
    with pytest.raises(PermissionError):
        archivepodcast.config.ArchivePodcastConfig(instance_path=tmp_path)


def test_config_permissions_error_write(place_test_config, tmp_path, mocker):
    """Mock a Permissions error with mock_open."""
    place_test_config("testing_true_valid.toml", tmp_path)

    conf = archivepodcast.config.ArchivePodcastConfig(instance_path=tmp_path)

    mock_open_func = mocker.mock_open(read_data="")
    mock_open_func.side_effect = PermissionError("Permission denied")

    mocker.patch("pathlib.Path.open", mock_open_func)

    # TEST: PermissionsError is raised.
    with pytest.raises(PermissionError):
        conf._write_config()


def test_dictionary_functions_of_config(place_test_config, tmp_path):
    """Test the functions in the config object that let it behave like a dictionary."""
    place_test_config("testing_true_valid.toml", tmp_path)

    conf = archivepodcast.config.ArchivePodcastConfig(instance_path=tmp_path)

    # TEST: __contains__ method.
    assert "app" in conf, "__contains__ method of config object doesn't work"

    # TEST: __repr__ method.
    assert isinstance(str(conf), str), "__repr__ method of config object doesn't work"

    # TEST: __getitem__ method.
    assert isinstance(conf["app"], dict), "__getitem__ method of config object doesn't work"

    from collections.abc import ItemsView

    # TEST: .items() method.
    assert isinstance(conf.items(), ItemsView), ".items() method of config object doesn't work"


def test_load_write_no_config_path(place_test_config, tmp_path):
    """Unit test  writing the config."""
    place_test_config("testing_true_valid.toml", tmp_path)

    conf = archivepodcast.config.ArchivePodcastConfig(instance_path=tmp_path)

    conf._config_path = None

    # TEST: PermissionsError is raised.
    with pytest.raises(ValueError, match="Config path not set, cannot load config"):
        conf._load_file()

    # TEST: PermissionsError is raised.
    with pytest.raises(ValueError, match="Config path not set, cannot write config"):
        conf._write_config()


def test_config_no_url_forward_slash(place_test_config, tmp_path, caplog):
    """Test config file loading, use tmp_path."""
    place_test_config("testing_true_no_forward_slash.toml", tmp_path)

    conf = archivepodcast.config.ArchivePodcastConfig(instance_path=tmp_path)

    assert conf["app"]["inet_path"][-1] == "/"
    assert conf["app"]["s3"]["cdn_domain"][-1] == "/"
