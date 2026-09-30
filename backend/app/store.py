from collections import defaultdict
from threading import Lock

from .database import IncidentEventRecord, IncidentRecord, SessionLocal
from .models import IncidentEvent


class EventStore:
    def __init__(self) -> None:
        self._events: dict[str, list[IncidentEvent]] = defaultdict(list)
        self._lock = Lock()
        self._load_from_db()

    def _load_from_db(self) -> None:
        with SessionLocal() as session:
            rows = session.query(IncidentEventRecord).order_by(IncidentEventRecord.timestamp).all()
            for row in rows:
                try:
                    event = IncidentEvent.model_validate({
                        "incident_id": row.incident_id,
                        "timestamp": row.timestamp,
                        "source": row.source,
                        "service": row.service,
                        "severity": row.severity,
                        "message": row.message,
                    })
                    self._events[row.incident_id].append(event)
                except Exception:
                    continue

    def add_many(self, events: list[IncidentEvent]) -> None:
        with self._lock:
            with SessionLocal() as session:
                for event in events:
                    self._events[event.incident_id].append(event)
                    session.add(IncidentEventRecord(
                        incident_id=event.incident_id,
                        timestamp=str(event.timestamp),
                        source=event.source,
                        service=event.service,
                        severity=event.severity.value,
                        message=event.message,
                    ))
                    if session.get(IncidentRecord, event.incident_id) is None:
                        session.add(IncidentRecord(
                            id=event.incident_id,
                            title=f"Incident {event.incident_id}",
                            severity=event.severity.value,
                            status="OPEN",
                        ))
                session.commit()

    def get(self, incident_id: str) -> list[IncidentEvent]:
        return sorted(self._events.get(incident_id, []), key=lambda event: event.timestamp)

    def incidents(self) -> list[str]:
        return sorted(self._events.keys())


store = EventStore()
