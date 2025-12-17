"""RSS/XML models using pydantic-xml for podcast feeds."""

from typing import Self

from pydantic import ConfigDict
from pydantic.config import ExtraValues
from pydantic_xml import BaseXmlModel, attr, element

# Namespace definitions for RSS feeds
NSMAP = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "googleplay": "http://www.google.com/schemas/play-podcasts/1.0",
    "media": "http://search.yahoo.com/mrss/",
    "podcast": "https://podcastindex.org/namespace/1.0",
    "sy": "http://purl.org/rss/1.0/modules/syndication/",
    "wfw": "http://wellformedweb.org/CommentAPI/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "slash": "http://purl.org/rss/1.0/modules/slash/",
    "rawvoice": "http://www.rawvoice.com/rawvoiceRssModule/",
    "spotify": "http://www.spotify.com/ns/rss/",
    "feedburner": "http://rssnamespace.org/feedburner/ext/1.0",
}

_EXTRA_MODE: ExtraValues = "forbid"


class Enclosure(BaseXmlModel, tag="enclosure"):
    """RSS enclosure element for media files."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    url: str = attr(default="")
    length: str | None = attr(default=None)
    type: str | None = attr(default=None)


class ItunesImage(BaseXmlModel, tag="image", nsmap={"itunes": NSMAP["itunes"]}, ns="itunes"):
    """iTunes image element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    href: str = attr(default="")


class Image(BaseXmlModel, tag="image"):
    """RSS image element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    url: str | None = element(default=None)
    title: str | None = element(default=None)
    link: str | None = element(default=None)


class MediaContent(BaseXmlModel, tag="content", nsmap={"media": NSMAP["media"]}, ns="media"):
    """Media RSS content element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    url: str = attr(default="")
    length: str | None = attr(default=None)
    type: str | None = attr(default=None)


class Item(BaseXmlModel, tag="item"):
    """RSS item/episode element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    title: str | None = element(default=None)
    link: str | None = element(default=None)
    description: str | None = element(default=None)
    pub_date: str | None = element(tag="pubDate", default=None)
    guid: str | None = element(default=None)
    enclosure: Enclosure | None = element(default=None)
    media_content: MediaContent | None = element(default=None)
    itunes_image: ItunesImage | None = element(default=None)


class AtomLink(BaseXmlModel, tag="link", nsmap={"atom": NSMAP["atom"]}, ns="atom"):
    """Atom link element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    href: str = attr(default="")
    rel: str | None = attr(default=None)
    type: str | None = attr(default=None)


class ItunesOwner(BaseXmlModel, tag="owner", nsmap={"itunes": NSMAP["itunes"]}, ns="itunes"):
    """iTunes owner element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    name: str | None = element(tag="name", ns="itunes", default=None)
    email: str | None = element(tag="email", ns="itunes", default=None)


class Channel(BaseXmlModel, tag="channel"):
    """RSS channel element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    title: str | None = element(default=None)
    link: str | None = element(default=None)
    description: str | None = element(default=None)
    language: str | None = element(default=None)
    image: Image | None = element(default=None)
    atom_link: AtomLink | None = element(default=None)
    itunes_image: ItunesImage | None = element(default=None)
    itunes_owner: ItunesOwner | None = element(default=None)
    itunes_author: str | None = element(tag="author", ns="itunes", default=None)
    itunes_new_feed_url: str | None = element(tag="new-feed-url", ns="itunes", default=None)
    items: list[Item] = element(tag="item", default_factory=list)


class Rss(BaseXmlModel, tag="rss", nsmap=NSMAP):
    """RSS root element."""

    model_config = ConfigDict(extra=_EXTRA_MODE)

    version: str = attr(default="2.0")
    channel: Channel | None = element(default=None)

    def has_episodes(self) -> bool:
        """Check if the feed has any episodes (items)."""
        if self.channel is None:
            return False
        return len(self.channel.items) > 0

    def episode_count(self) -> int:
        """Get the number of episodes in the feed."""
        if self.channel is None:
            return 0
        return len(self.channel.items)


class RssFeed:
    """Wrapper class for RSS feed handling with pydantic-xml.

    This class provides methods for parsing, serializing, and inspecting RSS feeds
    using pydantic-xml models.
    """

    def __init__(self, rss: Rss | None = None, raw_bytes: bytes | None = None) -> None:
        """Initialize RssFeed from either an Rss model or raw bytes."""
        self._rss: Rss | None = rss
        self._raw_bytes: bytes | None = raw_bytes
        self._parse_error: bool = False

        if rss is not None:
            result = rss.to_xml(encoding="UTF-8", xml_declaration=True)
            self._raw_bytes = result if isinstance(result, bytes) else result.encode("UTF-8")
        elif raw_bytes is not None:
            try:
                self._rss = Rss.from_xml(raw_bytes)
            except Exception as e:  # Catch all XML/validation errors (xml, pydantic, etc.)
                # Temporary debug logging
                import logging

                logger = logging.getLogger(__name__)
                logger.critical("RSS PARSE ERROR: %s", e, exc_info=True)
                self._rss = None
                self._parse_error = True

    @classmethod
    def from_rss(cls, rss: Rss) -> Self:
        """Create RssFeed from an Rss pydantic-xml model."""
        return cls(rss=rss)

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        """Create RssFeed from raw XML bytes."""
        return cls(raw_bytes=data)

    @property
    def rss(self) -> Rss | None:
        """Get the underlying Rss pydantic-xml model."""
        return self._rss

    @property
    def is_valid(self) -> bool:
        """Check if the feed is valid (successfully parsed)."""
        return self._rss is not None and not self._parse_error

    def to_bytes(self, *, encoding: str = "UTF-8") -> bytes:
        """Serialize the feed to XML bytes.

        Returns the original raw bytes if available (preserving exact formatting),
        otherwise serializes from the parsed model.
        """
        # Prefer original raw bytes to preserve exact formatting when available
        if self._raw_bytes is not None and self._rss is not None:
            return self._raw_bytes
        if self._rss is None:
            return b""
        result = self._rss.to_xml(encoding=encoding, xml_declaration=True)
        return result if isinstance(result, bytes) else result.encode(encoding)

    def has_episodes(self) -> bool:
        """Check if the feed has any episodes (items)."""
        if self._rss is not None and self._rss.has_episodes():
            return True
        # Fallback to raw bytes search for feeds with non-standard structure
        if self._raw_bytes is not None:
            return b"<item" in self._raw_bytes or b"<item>" in self._raw_bytes
        return False

    def episode_count(self) -> int:
        """Get the number of episodes in the feed."""
        if self._rss is not None:
            return self._rss.episode_count()
        # Fallback to raw bytes count for feeds with non-standard structure
        if self._raw_bytes is not None:
            return self._raw_bytes.count(b"<item") + self._raw_bytes.count(b"<item>")
        return 0
