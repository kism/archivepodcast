"""Profiler Utility."""

from pydantic import BaseModel


class EventLastTime(BaseModel):
    """Flat record of each event's last duration in seconds, keyed by path."""

    times: dict[str, float] = {}

    def set_event_time(self, path: str, duration: float) -> None:
        """Record the last duration of an event."""
        self.times[path.strip("/") or "root"] = duration


def get_event_times_str(event_times: EventLastTime) -> str:
    """Format the event times for logging."""
    msg = "Event times, async so anything can be held up by anything else in a pool >>>"
    return msg + "".join(f"\n {path}: {duration:.2f}s" for path, duration in sorted(event_times.times.items()))
