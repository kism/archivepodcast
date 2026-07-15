"""Profiler Utility."""

from typing import Any

from pydantic import BaseModel


class EventLastTime(BaseModel):
    """Flat record of each event's last duration in seconds, keyed by path."""

    times: dict[str, float] = {}

    def set_event_time(self, path: str, duration: float) -> None:
        """Record the last duration of an event."""
        self.times[path.strip("/") or "root"] = duration


def get_event_times_str(event_times: EventLastTime) -> str:
    """Format the event times for logging, indented as a tree."""
    root: dict[str, Any] = {"duration": event_times.times.get("root"), "children": {}}
    for path, duration in event_times.times.items():  # insertion order = completion order
        if path == "root":
            continue
        node = root
        for part in path.split("/"):
            node = node["children"].setdefault(part, {"duration": None, "children": {}})
        node["duration"] = duration

    def render(name: str, node: dict[str, Any], indent: int) -> list[str]:
        duration_str = f"{node['duration']:.2f}s" if node["duration"] is not None else "No duration"
        lines = [f"{' ' * indent}{name}: {duration_str}"]
        for child_name, child in node["children"].items():
            lines += render(child_name, child, indent + 2)
        return lines

    msg = "Event times, async so anything can be held up by anything else in a pool >>>\n"
    return msg + "\n".join(render("root", root, 1))
