from collections import defaultdict
from datetime import timedelta
from threading import Lock
import json
import re

from .database import IncidentEventRecord, IncidentRecord, SessionLocal
from .models import IncidentEvent


class EventStore:
    def __init__(self) -> None:
        self._events: dict[str, list[IncidentEvent]] = defaultdict(list)
        self._lock = Lock()
        self._load_from_db()

    @staticmethod
    def _row_to_event(row: IncidentEventRecord) -> IncidentEvent:
        metadata = {}
        if row.metadata_json:
            try:
                metadata = json.loads(row.metadata_json)
            except Exception:
                metadata = {}
        return IncidentEvent.model_validate({
            "incident_id": row.incident_id,
            "timestamp": row.timestamp,
            "source": row.source,
            "service": row.service,
            "severity": row.severity,
            "message": row.message,
            "metadata": metadata,
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
                pending_event_keys: set[tuple[str, str, str]] = set()
                for event in events:
                    existing = self._events[event.incident_id]
                    if not any(str(item.id) == str(event.id) for item in existing):
                        existing.append(event)
                    metadata = event.metadata or {}
                    client_id = metadata.get("client_id")
                    incident_record = session.get(IncidentRecord, event.incident_id)
                    if incident_record is None and event.incident_id not in pending_incidents:
                        session.add(IncidentRecord(
                            id=event.incident_id,
                            client_id=client_id,
                            title=f"{metadata.get('client_name') or event.service} incident",
                            severity=event.severity.value,
                            status="OPEN",
                        ))
                        pending_incidents.add(event.incident_id)
                        session.flush()
                    elif incident_record is not None and client_id and not incident_record.client_id:
                        incident_record.client_id = client_id
                    event_key = (event.incident_id, str(event.timestamp), event.message)
                    if event_key in pending_event_keys:
                        continue
                    pending_event_keys.add(event_key)
                    session.add(IncidentEventRecord(
                        incident_id=event.incident_id,
                        timestamp=str(event.timestamp),
                        source=event.source,
                        service=event.service,
                        severity=event.severity.value,
                        message=event.message,
                        metadata_json=json.dumps(metadata),
                    ))
                session.commit()

    def get(self, incident_id: str) -> list[IncidentEvent]:
        # PostgreSQL is the source of truth so horizontally scaled replicas never serve
        # permanently stale incident state from a process-local memory cache.
        try:
            with SessionLocal() as session:
                rows = session.query(IncidentEventRecord).filter(
                    IncidentEventRecord.incident_id == incident_id
                ).order_by(IncidentEventRecord.timestamp).all()
                events: list[IncidentEvent] = []
                for row in rows:
                    try:
                        events.append(self._row_to_event(row))
                    except Exception:
                        continue
                if events:
                    self._events[incident_id] = events
                return events
        except Exception:
            # Availability fallback: if the database briefly fails, serve the last
            # process-local copy rather than crashing the incident dashboard.
            return sorted(self._events.get(incident_id, []), key=lambda event: event.timestamp)

    def incidents(self) -> list[str]:
        """Return incident IDs with short-window duplicates collapsed per client."""
        with SessionLocal() as session:
            rows = session.query(
                IncidentRecord.id,
                IncidentRecord.client_id,
                IncidentRecord.title,
                IncidentRecord.created_at,
            ).order_by(IncidentRecord.created_at.desc()).all()
        ids: list[str] = []
        latest_by_fingerprint: dict[tuple[str, str], object] = {}
        for row in rows:
            client_key = str(row.client_id or "")
            title_key = re.sub(r"\s+", " ", str(row.title or "").strip().lower())
            fingerprint = (client_key, title_key)
            created = row.created_at
            previous = latest_by_fingerprint.get(fingerprint)
            if previous is not None and created is not None:
                try:
                    if previous - created <= timedelta(minutes=15):
                        continue
                except TypeError:
                    pass
            latest_by_fingerprint[fingerprint] = created
            ids.append(row.id)
        for incident_id in ids:
            self.get(incident_id)
        return ids

    def incident_client_id(self, incident_id: str) -> str | None:
        with SessionLocal() as session:
            row = session.get(IncidentRecord, incident_id)
            return row.client_id if row else None


store = EventStore()
