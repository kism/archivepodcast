"""Helper functions for rss processing."""

import xml.etree.ElementTree as ET
from typing import Any


def tree_no_episodes(tree: ET.ElementTree[Any] | None) -> bool:
    """Check if the XML tree has no episodes."""
    if tree is None:
        return True
    return len(tree.findall(".//item")) == 0
