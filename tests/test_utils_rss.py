from pathlib import Path

from lxml import etree

from archivepodcast.utils.rss import tree_no_episodes
from tests.constants import DUMMY_RSS_STR


def test_tree_no_episodes_none() -> None:
    """Test tree_no_episodes with None input."""
    assert tree_no_episodes(None) is True


def test_tree_no_episodes_with_episodes() -> None:
    """Test tree_no_episodes with episodes present."""
    tree = etree.fromstring(bytes(DUMMY_RSS_STR, encoding="utf-8"))
    assert tree_no_episodes(etree.ElementTree(tree)) is False


def test_tree_no_episodes_with_episodes_disk(tmp_path: Path) -> None:
    """Test tree_no_episodes with episodes present."""
    rss_path = tmp_path / "test.rss"
    rss_path.write_text(DUMMY_RSS_STR)

    with rss_path.open() as file:
        tree = etree.parse(file)

    assert tree_no_episodes(tree) is False
