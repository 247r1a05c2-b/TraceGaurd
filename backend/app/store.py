from collections import defaultdict
from threading import Lock

from .models import IncidentEvent


class EventStore:
    def __init__(self) -> None:
        self._events: dict[str, list[IncidentEvent]] = defaultdict(list)
        self._lock = Lock()

    def add_many(self, events: list[IncidentEvent]) -> None:
        with self._lock:
            for event in events:
                self._events[event.incident_id].append(event)

    def get(self, incident_id: str) -> list[IncidentEvent]:
        return sorted(self._events.get(incident_id, []), key=lambda event: event.timestamp)

    def incidents(self) -> list[str]:
        return sorted(self._events.keys())


store = EventStore()
