from fastapi import FastAPI, HTTPException

from .models import IncidentSummary, IngestRequest, IngestResponse
from .normalizer import normalize_events
from .simulator import available_scenarios, generate_scenario
from .store import store

app = FastAPI(
    title="TraceGaurd API",
    version="0.1.0",
    description="Phase 1 incident ingestion and normalization service.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/scenarios")
def scenarios() -> dict[str, str]:
    return available_scenarios()


@app.post("/api/v1/simulate/{scenario}", response_model=IngestResponse)
def simulate(scenario: str) -> IngestResponse:
    try:
        events = generate_scenario(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    normalized = normalize_events(events)
    store.add_many(normalized)
    return IngestResponse(
        accepted=len(normalized),
        incident_ids=sorted({event.incident_id for event in normalized}),
    )


@app.post("/api/v1/events", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
    normalized = normalize_events(request.events)
    store.add_many(normalized)
    return IngestResponse(
        accepted=len(normalized),
        incident_ids=sorted({event.incident_id for event in normalized}),
    )


@app.get("/api/v1/incidents", response_model=list[IncidentSummary])
def list_incidents() -> list[IncidentSummary]:
    severity_order = {"info": 0, "warning": 1, "critical": 2}
    summaries = []
    for incident_id in store.incidents():
        events = store.get(incident_id)
        severity = max(events, key=lambda event: severity_order[event.severity.value]).severity
        summaries.append(
            IncidentSummary(
                incident_id=incident_id,
                title=f"Incident {incident_id}",
                status="OPEN",
                severity=severity,
                event_count=len(events),
            )
        )
    return summaries


@app.get("/api/v1/incidents/{incident_id}/events")
def incident_events(incident_id: str):
    events = store.get(incident_id)
    if not events:
        raise HTTPException(status_code=404, detail="Incident not found")
    return events
