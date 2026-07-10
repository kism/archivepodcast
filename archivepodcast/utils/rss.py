"""Helper functions for rss processing."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lxml import etree


def tree_no_episodes(tree: etree._ElementTree | None) -> bool:
    """Check if the XML tree has no episodes."""
    if tree is None:
        return True
    return len(tree.xpath("//item")) == 0
