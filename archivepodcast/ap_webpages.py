"""Webpage cache module."""

class Webpage:
    """Webpage object."""

    def __init__(self, path: str, mime: str, content: str | bytes) -> None:
        """Initialise the Webpages object."""
        # Mime types that magic doesn't always get right
        if path.endswith(".js"):
            mime = "text/javascript"
        elif path.endswith(".css"):
            mime = "text/css"
        elif path.endswith(".woff2"):
            mime = "font/woff2"

        self.path: str = path
        self.mime: str = mime
        self.content: str | bytes = content


class Webpages:
    """Webpage object."""

    def __init__(self) -> None:
        """Initialise the Webpages object."""
        self._webpages: dict[str, Webpage] = {}

    def __len__(self) -> int:
        """Return the length of the webpages."""
        return len(self._webpages)

    def add(self, path: str, mime: str, content: str | bytes) -> None:
        """Add a webpage."""
        self._webpages[path] = Webpage(path=path, mime=mime, content=content)

    def get_all(self) -> dict[str, Webpage]:
        """Return the webpages."""
        return self._webpages

    def get_webpage(self, path: str) -> Webpage:
        """Get a webpage."""
        return self._webpages[path]
