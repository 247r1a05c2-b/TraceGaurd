from datetime import datetime, timedelta, timezone

from .models import EventType, IncidentEvent, Severity


def checkout_incident() -> list[IncidentEvent]:
    base = datetime.now(timezone.utc).replace(microsecond=0)
    incident_id = "INC-1001"

    return [
        IncidentEvent(
            incident_id=incident_id,
            source=EventType.deployment,
            timestamp=base,
            service="Checkout",
            severity=Severity.info,
            message="Deployment v2.8.1 completed successfully",
            metadata={"version": "v2.8.1"},
        ),
        IncidentEvent(
            incident_id=incident_id,
            source=EventType.alert,
            timestamp=base + timedelta(minutes=1),
            service="Checkout",
            severity=Severity.critical,
            message="HTTP 500 error rate crossed 20%",
            metadata={"rate": 0.21},
        ),
        IncidentEvent(
            incident_id=incident_id,
            source=EventType.log,
            timestamp=base + timedelta(minutes=2),
            service="Database",
            severity=Severity.critical,
            message="Connection pool timeout detected",
            metadata={"timeout_ms": 3000},
        ),
        IncidentEvent(
            incident_id=incident_id,
            source=EventType.ticket,
            timestamp=base + timedelta(minutes=3),
            service="Support",
            severity=Severity.warning,
            message="Customers report checkout failures",
            metadata={"ticket_count": 17},
        ),
    ]


def available_scenarios() -> dict[str, str]:
    return {"checkout": "Simulated checkout deployment incident"}


def generate_scenario(name: str) -> list[IncidentEvent]:
    if name == "checkout":
        return checkout_incident()
    raise ValueError(f"Unknown scenario: {name}")
