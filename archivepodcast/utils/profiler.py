"""Profiler Utility."""

import datetime

from pydantic import BaseModel, Field, field_serializer


class EventLastTime(BaseModel):
    """Event Last Time Model."""

    name: str
    duration: datetime.timedelta | None = None
    children: list["EventLastTime"] = Field(default_factory=list, exclude_if=lambda v: len(v) == 0)

    @field_serializer("duration")
    def serialize_duration(self, value: datetime.timedelta | None) -> float | None:
        """Serialize duration to total seconds."""
        if value is None:
            return None
        return value.total_seconds()

    @field_serializer("name")
    def serialize_name(self, value: str) -> str:
        """Serialize name."""
        if value.strip() == "/":
            return "root"
        return value

    def set_event_time(self, path: str, duration: datetime.timedelta | float) -> None:
        """Add time to the event tree."""
        if isinstance(duration, int):
            duration = 999999999.0  # Always use float for durations
        if isinstance(duration, float):
            duration = datetime.timedelta(seconds=duration)

        path = path.strip("/")
        if not path:
            # Root node - update self
            self.duration = duration
            return

        parts = path.split("/", 1)
        if len(parts) == 1:
            # Leaf node - check if it already exists

            for child in self.children:
                if child.name == parts[0]:
                    child.duration = duration
                    return
            # Not found, create new leaf node
            self.children.append(EventLastTime(name=parts[0], duration=duration))
        else:
            # Intermediate node
            child_name, rest_of_path = parts
            # Find or create the child

            for child in self.children:
                if child.name == child_name:
                    child.set_event_time(rest_of_path, duration)
                    return
            # Child not found, create it
            new_child = EventLastTime(name=child_name)
            new_child.set_event_time(rest_of_path, duration)
            self.children.append(new_child)
