from collections import defaultdict
from threading import Lock

from .database import IncidentEventRecord, IncidentRecord, SessionLocal
from .models import IncidentEvent


class EventStore:
    def __init__(self) -> None:
        self._events: dict[str, list[IncidentEvent]] = defaultdict(list)
        self._lock = Lock()
        self._load_from_db()

    @staticmethod
    def _row_to_event(row: IncidentEventRecord) -> IncidentEvent:
        return IncidentEvent.model_validate({
            "incident_id": row.incident_id,
            "timestamp": row.timestamp,
            "source": row.source,
            "service": row.service,
            "severity": row.severity,
            "message": row.message,
        })

    def _load_from_db(self) -> None:
        with SessionLocal() as session:
            rows = session.query(IncidentEventRecord).order_by(IncidentEventRecord.timestamp).all()
            for row in rows:
                try:
                    self._events[row.incident_id].append(self._row_to_event(row))
                except Exception:
                    continue

    def add_many(self, events: list[IncidentEvent]) -> None:
        if not events:
            return
        with self._lock:
            with SessionLocal() as session:
                pending_incidents: set[str] = set()
                for event in events:
                    existing = self._events[event.incident_id]
                    if not any(str(item.id) == str(event.id) for item in existing):
                        existing.append(event)
                    session.add(IncidentEventRecord(
                        incident_id=event.incident_id,
                        timestamp=str(event.timestamp),
                        source=event.source,
                        service=event.service,
                        severity=event.severity.value,
                        message=event.message,
                    ))
                    if event.incident_id not in pending_incidents and session.get(IncidentRecord, event.incident_id) is None:
                        session.add(IncidentRecord(
                            id=event.incident_id,
                            title=f"Incident {event.incident_id}",
                            severity=event.severity.value,
                            status="OPEN",
                        ))
                        pending_incidents.add(event.incident_id)
                session.commit()

    def get(self, incident_id: str) -> list[IncidentEvent]:
        cached = self._events.get(incident_id, [])
        if cached:
            return sorted(cached, key=lambda event: event.timestamp)
        with SessionLocal() as session:
            rows = session.query(IncidentEventRecord).filter(IncidentEventRecord.incident_id == incident_id).order_by(IncidentEventRecord.timestamp).all()
            events: list[IncidentEvent] = []
            for row in rows:
                try:
                    events.append(self._row_to_event(row))
                except Exception:
                    continue
            if events:
                self._events[incident_id] = events
            return events

    def incidents(self) -> list[str]:
        with SessionLocal() as session:
            rows = session.query(IncidentRecord.id).order_by(IncidentRecord.created_at.desc()).all()
            ids = [row[0] for row in rows]
        for incident_id in ids:
            self.get(incident_id)
        return ids


store = EventStore()
