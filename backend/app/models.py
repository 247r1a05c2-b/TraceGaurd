from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    log = "log"
    alert = "alert"
    deployment = "deployment"
    ticket = "ticket"
    chat = "chat"


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class IncidentEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    incident_id: str
    source: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service: str
    severity: Severity = Severity.info
    message: str
    metadata: dict = Field(default_factory=dict)


class IncidentSummary(BaseModel):
    incident_id: str
    client_id: str | None = None
    title: str
    status: str
    severity: Severity
    event_count: int


class IngestRequest(BaseModel):
    events: list[IncidentEvent]


class IngestResponse(BaseModel):
    accepted: int
    incident_ids: list[str]
