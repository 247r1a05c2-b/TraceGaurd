from .models import IncidentEvent


def normalize_event(event: IncidentEvent) -> IncidentEvent:
    return event.model_copy(update={
        "service": event.service.strip().lower(),
        "message": " ".join(event.message.split()),
    })


def normalize_events(events: list[IncidentEvent]) -> list[IncidentEvent]:
    return [normalize_event(event) for event in events]
