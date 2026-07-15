"""Test the profiler output formatting."""

from archivepodcast.utils.profiler import EventLastTime, get_event_times_str


def test_get_event_times_str_indents_tree() -> None:
    """Nested paths render indented under their parents, root first."""
    event_times = EventLastTime()
    event_times.set_event_time("grab_podcasts/Scrape/lemon", 3.08)
    event_times.set_event_time("grab_podcasts/Scrape", 3.09)
    event_times.set_event_time("grab_podcasts", 6.14)
    event_times.set_event_time("/", 6.93)

    assert get_event_times_str(event_times) == (
        "Event times, async so anything can be held up by anything else in a pool >>>\n"
        " root: 6.93s\n"
        "   grab_podcasts: 6.14s\n"
        "     Scrape: 3.09s\n"
        "       lemon: 3.08s"
    )
