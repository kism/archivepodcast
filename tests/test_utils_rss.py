from pathlib import Path
import xml.etree.ElementTree as ET

from archivepodcast.utils.rss import tree_no_episodes
from tests.constants import DUMMY_RSS_STR


def test_tree_no_episodes_none() -> None:
    """Test tree_no_episodes with None input."""
    assert tree_no_episodes(None) is True


def test_tree_no_episodes_with_episodes() -> None:
    """Test tree_no_episodes with episodes present."""
    root = ET.fromstring(DUMMY_RSS_STR)
    assert tree_no_episodes(ET.ElementTree(root)) is False


def test_tree_no_episodes_with_episodes_disk(tmp_path: Path) -> None:
    """Test tree_no_episodes with episodes present."""
    rss_path = tmp_path / "test.rss"
    rss_path.write_text(DUMMY_RSS_STR)

    tree = ET.parse(rss_path)

    assert tree_no_episodes(tree) is False
