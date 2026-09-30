from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agents import run_agents
from .guardrails import classify_action
from .models import IncidentSummary, IngestRequest, IngestResponse
from .normalizer import normalize_events
from .simulator import available_scenarios, generate_scenario
from .store import store

app = FastAPI(title="TraceGaurd API", version="2.0.0", description="LangGraph multi-agent AI incident commander")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "tracegaurd-api", "version": "2.0.0"}

@app.get("/api/v1/scenarios")
def scenarios():
    return available_scenarios()

@app.post("/api/v1/simulate/{scenario}", response_model=IngestResponse)
def simulate(scenario: str):
    try:
        events = generate_scenario(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    normalized = normalize_events(events)
    store.add_many(normalized)
    return IngestResponse(accepted=len(normalized), incident_ids=sorted({e.incident_id for e in normalized}))

@app.post("/api/v1/events", response_model=IngestResponse)
def ingest(request: IngestRequest):
    normalized = normalize_events(request.events)
    store.add_many(normalized)
    return IngestResponse(accepted=len(normalized), incident_ids=sorted({e.incident_id for e in normalized}))

@app.get("/api/v1/incidents", response_model=list[IncidentSummary])
def list_incidents():
    severity_order = {"info": 0, "warning": 1, "critical": 2}
    summaries = []
    for incident_id in store.incidents():
        events = store.get(incident_id)
        severity = max(events, key=lambda e: severity_order[e.severity.value]).severity
        summaries.append(IncidentSummary(incident_id=incident_id, title=f"Incident {incident_id}", status="OPEN", severity=severity, event_count=len(events)))
    return summaries

@app.get("/api/v1/incidents/{incident_id}/events")
def incident_events(incident_id: str):
    events = store.get(incident_id)
    if not events:
        raise HTTPException(status_code=404, detail="Incident not found")
    return events

@app.get("/api/v1/incidents/{incident_id}/analysis")
def incident_analysis(incident_id: str):
    events = store.get(incident_id)
    if not events:
        raise HTTPException(status_code=404, detail="Incident not found")
    return run_agents([event.model_dump(mode="json") for event in events])

@app.post("/api/v1/guardrails/check")
def guardrail_check(payload: dict):
    return classify_action(payload.get("action", ""))
