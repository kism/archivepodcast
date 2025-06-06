"""Webpage caching and management."""

from typing import ClassVar


class Webpage:
    """Represents a cached webpage with its metadata."""

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
    """Manages a collection of cached webpages."""

    WEBPAGE_NICE_NAMES: ClassVar[dict[str, str]] = {
        "index.html": "Home",
        "guide.html": "Guide",
        "filelist.html": "File List",
        "webplayer.html": "Web Player",
        "about.html": "About",
    }

    def __init__(self) -> None:
        """Initialise the Webpages object."""
        self._webpages: dict[str, Webpage] = {}

    def __len__(self) -> int:
        """Return the length of the webpages."""
        return len(self._webpages)

    def get_list(self) -> dict[str, str]:
        """Return the items of the webpages."""
        item_list = self._webpages.items()

        return_value = {}
        for _, value in item_list:
            return_value[value.path] = value.mime

        return return_value

    def add(self, path: str, mime: str, content: str | bytes) -> None:
        """Add a webpage."""
        self._webpages[path] = Webpage(path=path, mime=mime, content=content)

    def get_all(self) -> dict[str, Webpage]:
        """Return the webpages."""
        return self._webpages

    def get_webpage(self, path: str) -> Webpage:
        """Get a webpage."""
        return self._webpages[path]

    def generate_header(self, path: str, *, debug: bool = False) -> str:
        """Get the header for a webpage."""
        reload_a_tag = """
 | <a href="#" onclick="
const originalText = document.getElementById('debug_status').innerHTML;

function resetText() {
    document.getElementById('debug_status').innerHTML = originalText;
}

fetch('/api/reload')
.then(response => response.json())
.then(data => {
    console.log(data.msg);
    document.getElementById('debug_status').innerHTML = 'RELOAD SENT';
    setTimeout(resetText, 3000);
})
.catch(error => console.error(error));
return false;
">Reload</a>"""

        header = "<header>"

        for webpage in self.WEBPAGE_NICE_NAMES:
            if webpage == "about.html":
                about_page_exists = self._webpages.get("about.html") or path == "about.html"
                if not about_page_exists:
                    continue

            if webpage == path:
                header += f'<div class="active">{self.WEBPAGE_NICE_NAMES[webpage]}</div> | '
            else:
                header += f'<a href="{webpage}">{self.WEBPAGE_NICE_NAMES[webpage]}</a> | '

        header = header[:-3]

        if debug:
            if path != "health.html":
                header += ' | <a href="/health">Health</a>'
            else:
                header += ' | <div class="active">Health</div>'
            header += reload_a_tag.replace("\n", "")
            header += ' | <a href="/console" target="_blank">Flask Console</a>'
            header += ' | <a id="debug_status" style="color: #ff0000">DEBUG ENABLED</a>'

        header += "<hr></header>"
        return header
