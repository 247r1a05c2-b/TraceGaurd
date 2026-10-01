from collections import Counter
from datetime import datetime, timezone
import json
import os
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .agents import run_agents
from .database import AuditRecord, ClientRecord, UserRecord, database_status, SessionLocal
from .guardrails import classify_action
from .models import IncidentEvent, IncidentSummary, IngestRequest, IngestResponse, Severity
from .monitoring import audit_log, calculate_client_score, clients, execute_approved_action, execution_log, heartbeat, check_website, hydrate_clients, record_audit, register_client
from .normalizer import normalize_events
from .security import issue_token, verify_credentials, verify_token
from .simulator import available_scenarios, generate_scenario
from .store import store

app = FastAPI(title="TraceGaurd API", version="4.1.0", description="Multi-client incident monitoring, multi-agent RCA, RAG evidence, human guardrails and controlled remediation")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
bearer = HTTPBearer(auto_error=False)

with SessionLocal() as _session:
    _records = _session.query(ClientRecord).all()
    hydrate_clients([{
        "id": x.id, "name": x.name, "environment": x.environment, "service": x.service,
        "website_url": x.website_url, "health_path": x.health_path, "incidents": x.incidents,
        "status": x.status, "last_seen": x.last_seen.isoformat() if x.last_seen else None,
        "last_response_ms": x.last_response_ms, "last_http_status": x.last_http_status,
    } for x in _records])


class LoginRequest(BaseModel):
    email: str
    password: str


class ClientRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    environment: str = Field(default="production", max_length=50)
    service: str = Field(min_length=2, max_length=120)
    website_url: str | None = Field(default=None, max_length=1000)
    health_path: str = Field(default="/", max_length=250)


class ApprovalRequest(BaseModel):
    action: str
    approved: bool


class ExecuteRequest(BaseModel):
    action: str
    approval_id: str


def current_engineer(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Engineer login required")
    email = verify_token(credentials.credentials)
    if not email:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return email


def persist_client(client: dict) -> None:
    with SessionLocal() as session:
        session.merge(ClientRecord(
            id=client["client_id"], name=client["name"], environment=client["environment"],
            service=client["service"], website_url=client.get("website_url"), health_path=client.get("health_path", "/"),
            incidents=client.get("incidents", 0), status=client.get("status", "ONLINE"),
            last_seen=datetime.fromisoformat(client["last_seen"]) if client.get("last_seen") else None,
            last_response_ms=client.get("last_response_ms"), last_http_status=client.get("last_http_status")
        ))
        session.commit()


def persisted_audits() -> list[dict]:
    with SessionLocal() as session:
        rows = session.query(AuditRecord).order_by(AuditRecord.created_at.asc()).all()
    result = []
    for row in rows:
        try:
            details = json.loads(row.details or "{}")
        except Exception:
            details = {}
        result.append({"timestamp": row.created_at.isoformat() if row.created_at else None, "event": row.event, "actor": row.actor, "details": details})
    return result


def client_score(client_id: str) -> dict:
    client = clients.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    events = []
    for incident_id in store.incidents():
        events.extend(store.get(incident_id))
    score = calculate_client_score(client, events, persisted_audits())
    return {"client_id": client_id, "client_name": client["name"], **score}


@app.get("/health")
def health():
    return {"status": "ok", "service": "tracegaurd-api", "version": "4.1.0", "database": database_status(), "clients": len(clients)}


@app.get("/api/v1/database/status")
def db_status(engineer: str = Depends(current_engineer)):
    return database_status()


@app.post("/api/v1/auth/login")
def login(request: LoginRequest):
    if not verify_credentials(request.email, request.password):
        raise HTTPException(status_code=401, detail="Invalid engineer credentials")
    token = issue_token(request.email)
    with SessionLocal() as session:
        if session.get(UserRecord, request.email.lower()) is None:
            session.add(UserRecord(email=request.email.lower(), role="SOFTWARE_ENGINEER"))
            session.commit()
    record_audit("LOGIN", request.email, {})
    return {"access_token": token, "token_type": "bearer", "engineer": request.email.lower()}


@app.get("/api/v1/auth/me")
def me(engineer: str = Depends(current_engineer)):
    return {"email": engineer, "role": "SOFTWARE_ENGINEER", "permissions": ["MONITOR", "ANALYZE", "APPROVE", "EXECUTE_APPROVED_ACTIONS"]}


@app.get("/api/v1/scenarios")
def scenarios(engineer: str = Depends(current_engineer)):
    return available_scenarios()


@app.get("/api/v1/clients")
def list_clients(engineer: str = Depends(current_engineer)):
    result = []
    for client in clients.values():
        item = dict(client)
        item["performance"] = client_score(client["client_id"])
        item["score"] = item["performance"]["score"]
        result.append(item)
    return result


@app.get("/api/v1/clients/{client_id}/score")
def get_client_score(client_id: str, engineer: str = Depends(current_engineer)):
    return client_score(client_id)


@app.post("/api/v1/clients")
def add_client(request: ClientRequest, engineer: str = Depends(current_engineer)):
    try:
        client = register_client(request.name, request.environment, request.service, request.website_url, request.health_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    persist_client(client)
    record_audit("CLIENT_REGISTERED", engineer, client)
    client["performance"] = client_score(client["client_id"])
    client["score"] = client["performance"]["score"]
    return client


@app.delete("/api/v1/clients/{client_id}")
def delete_client(client_id: str, engineer: str = Depends(current_engineer)):
    client = clients.pop(client_id, None)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    with SessionLocal() as session:
        record = session.get(ClientRecord, client_id)
        if record is not None:
            session.delete(record)
            session.commit()
    record_audit("CLIENT_REMOVED", engineer, {"client_id": client_id, "name": client.get("name")})
    return {"removed": True, "client_id": client_id, "name": client.get("name"), "message": "Client removed from active monitoring. Historical incidents are preserved."}


@app.post("/api/v1/clients/{client_id}/heartbeat")
def client_heartbeat(client_id: str, engineer: str = Depends(current_engineer)):
    try:
        result = heartbeat(client_id)
        persist_client(result)
        record_audit("CLIENT_HEARTBEAT", engineer, {"client_id": client_id})
        return {**result, "performance": client_score(client_id), "score": client_score(client_id)["score"]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Client not found") from exc


@app.post("/api/v1/clients/{client_id}/check")
def client_check(client_id: str, engineer: str = Depends(current_engineer)):
    try:
        result = check_website(client_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Client not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    client = clients[client_id]
    persist_client(client)
    record_audit("WEBSITE_HEALTH_CHECK", engineer, result)
    if not result["healthy"]:
        incident_id = f"WEB-{uuid4().hex[:10]}"
        status_text = result.get("http_status") or "NO_RESPONSE"
        event = IncidentEvent(
            incident_id=incident_id,
            source="alert",
            service=client["service"],
            severity=Severity.critical if result.get("status") == "DOWN" else Severity.warning,
            message=f"{client['name']} website health check failed for {result['url']}: status={status_text}; response_ms={result['response_ms']}; error={result.get('error', 'unhealthy response')}",
            metadata={"client_id": client_id, "client_name": client["name"], "website_url": result["url"], "http_status": result.get("http_status"), "response_ms": result["response_ms"], "tokens": max(1, len(result.get("error", "")) // 4)},
        )
        store.add_many([event])
        client["incidents"] += 1
        persist_client(client)
        record_audit("CLIENT_INCIDENT_CREATED", client_id, {"client_id": client_id, "incident_id": incident_id, "reason": event.message})
        result["incident_id"] = incident_id
    result["performance"] = client_score(client_id)
    result["score"] = result["performance"]["score"]
    return result


@app.post("/api/v1/clients/{client_id}/simulate-incident", response_model=IngestResponse)
def simulate_client_incident(client_id: str, engineer: str = Depends(current_engineer)):
    client = clients.get(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    incident_id = f"INC-{uuid4().hex[:10]}"
    variant = sum(ord(char) for char in client_id) % 4
    patterns = [
        ("Database connection-pool pressure", "checkout deployment increased database connection demand; connection-pool timeouts and HTTP 500s followed"),
        ("Upstream payment-provider latency", "payment provider latency increased after the release; upstream timeouts caused elevated HTTP 502 and checkout failures"),
        ("Cache saturation after deployment", "cache hit ratio dropped after deployment; cache misses increased application latency and produced HTTP 500 responses"),
        ("Rate-limit configuration regression", "a new rate-limit configuration rejected normal client traffic and produced elevated HTTP 429 responses"),
    ]
    root_hint, failure_hint = patterns[variant]
    events = [
        IncidentEvent(incident_id=incident_id, source="deployment", service=client["service"], severity=Severity.warning, message=f"{client['name']} deployment completed in {client['environment']}: {root_hint}", metadata={"client_id": client_id, "client_name": client["name"], "tokens": 34}),
        IncidentEvent(incident_id=incident_id, source="log", service=client["service"], severity=Severity.critical, message=f"{client['name']} application error: {failure_hint}", metadata={"client_id": client_id, "client_name": client["name"], "tokens": 42}),
        IncidentEvent(incident_id=incident_id, source="alert", service=client["service"], severity=Severity.critical, message=f"{client['name']} health monitor detected elevated failure rate for {client.get('website_url') or client['service']}", metadata={"client_id": client_id, "client_name": client["name"], "tokens": 26}),
        IncidentEvent(incident_id=incident_id, source="ticket", service=client["service"], severity=Severity.warning, message=f"Customer support reports {client['name']} service degradation during the incident window", metadata={"client_id": client_id, "client_name": client["name"], "tokens": 22}),
    ]
    store.add_many(events)
    client["incidents"] += 1
    client["status"] = "DEGRADED"
    client["last_seen"] = datetime.now(timezone.utc).isoformat()
    persist_client(client)
    record_audit("CLIENT_INCIDENT_SIMULATED", client_id, {"client_id": client_id, "client_name": client["name"], "incident_id": incident_id, "root_hint": root_hint})
    return IngestResponse(accepted=len(events), incident_ids=[incident_id])


@app.post("/api/v1/simulate/{scenario}", response_model=IngestResponse)
def simulate(scenario: str, engineer: str = Depends(current_engineer)):
    try:
        events = generate_scenario(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    normalized = normalize_events(events)
    store.add_many(normalized)
    event_services = {str(e.service).lower() for e in normalized}
    for client in clients.values():
        service = client["service"].lower()
        if service in event_services or any(service.split("-")[0] in item for item in event_services):
            client["incidents"] += 1
            persist_client(client)
    record_audit("INCIDENT_INGESTED", engineer, {"scenario": scenario, "events": len(normalized)})
    return IngestResponse(accepted=len(normalized), incident_ids=sorted({e.incident_id for e in normalized}))


@app.post("/api/v1/events", response_model=IngestResponse)
def ingest(request: IngestRequest, engineer: str = Depends(current_engineer)):
    normalized = normalize_events(request.events)
    store.add_many(normalized)
    record_audit("EVENTS_INGESTED", engineer, {"events": len(normalized)})
    return IngestResponse(accepted=len(normalized), incident_ids=sorted({e.incident_id for e in normalized}))


@app.get("/api/v1/incidents", response_model=list[IncidentSummary])
def list_incidents(engineer: str = Depends(current_engineer)):
    severity_order = {"info": 0, "warning": 1, "critical": 2}
    summaries = []
    for incident_id in store.incidents():
        events = store.get(incident_id)
        if not events:
            continue
        severity = max(events, key=lambda e: severity_order[e.severity.value]).severity
        client_id = store.incident_client_id(incident_id) or next((e.metadata.get("client_id") for e in events if e.metadata.get("client_id")), None)
        client_name = clients.get(client_id, {}).get("name") if client_id else None
        title = f"{client_name} incident" if client_name else f"Incident {incident_id}"
        summaries.append(IncidentSummary(incident_id=incident_id, client_id=client_id, title=title, status="OPEN", severity=severity, event_count=len(events)))
    return summaries


@app.get("/api/v1/incidents/{incident_id}/events")
def incident_events(incident_id: str, engineer: str = Depends(current_engineer)):
    events = store.get(incident_id)
    if not events:
        raise HTTPException(status_code=404, detail="Incident not found")
    return events


@app.get("/api/v1/incidents/{incident_id}/analysis")
def incident_analysis(incident_id: str, engineer: str = Depends(current_engineer)):
    events = store.get(incident_id)
    if not events:
        raise HTTPException(status_code=404, detail="Incident not found")
    client_id = store.incident_client_id(incident_id) or next((e.metadata.get("client_id") for e in events if e.metadata.get("client_id")), None)
    result = run_agents([event.model_dump(mode="json") for event in events])
    result["client_id"] = client_id
    result["client"] = clients.get(client_id) if client_id else None
    result["client_performance"] = client_score(client_id) if client_id and client_id in clients else None
    result["diagnosis_steps"] = result.get("diagnosis_steps") or result.get("steps", [])
    result["repair_steps"] = result.get("repair_steps") or [{"stage": "Prepare safe remediation", "finding": action.get("action", ""), "validation": action.get("reason", "")} for action in result.get("actions", [])]
    result["evaluation"] = evaluate_analysis(result)
    result["approval_state"] = "PENDING_HUMAN_REVIEW" if any(a.get("risk") == "APPROVAL" for a in result.get("actions", [])) else "SAFE"
    return result


def evaluate_analysis(result: dict) -> dict:
    evidence_count = len(result.get("evidence", []))
    rag_count = len(result.get("rag_context", []))
    trace_count = len(result.get("agent_trace", []))
    confidence = int(result.get("confidence", 0))
    evidence_score = min(85, evidence_count * 12 + rag_count * 8)
    workflow_score = min(85, trace_count * 10)
    consistency = min(85, round((confidence * 0.55) + (evidence_score * 0.25) + (workflow_score * 0.20)))
    return {"root_cause_confidence": min(85, confidence), "evidence_coverage": evidence_score, "workflow_completeness": workflow_score, "diagnosis_quality": consistency, "explanation": "Confidence is an evidence-weighted hypothesis score and is capped at 85 in the presentation metrics."}


@app.post("/api/v1/incidents/{incident_id}/approve")
def approve_action(incident_id: str, request: ApprovalRequest, engineer: str = Depends(current_engineer)):
    if not store.get(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    classification = classify_action(request.action)
    if classification.get("risk") == "BLOCKED":
        raise HTTPException(status_code=403, detail="Guardrail blocked this action")
    approval_id = f"approval-{len(audit_log) + 1}"
    state = "APPROVED" if request.approved else "REJECTED"
    with SessionLocal() as session:
        from .database import ApprovalRecord
        session.add(ApprovalRecord(id=approval_id, incident_id=incident_id, action=request.action, engineer=engineer, state=state))
        session.commit()
    record_audit("HUMAN_APPROVAL", engineer, {"incident_id": incident_id, "action": request.action, "state": state, "approval_id": approval_id})
    return {"approval_id": approval_id, "incident_id": incident_id, "action": request.action, "state": state, "guardrail": classification}


@app.post("/api/v1/incidents/{incident_id}/execute")
def execute_action(incident_id: str, request: ExecuteRequest, engineer: str = Depends(current_engineer)):
    if not store.get(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    approved = any(x.get("event") == "HUMAN_APPROVAL" and x.get("details", {}).get("approval_id") == request.approval_id and x.get("details", {}).get("state") == "APPROVED" and x.get("details", {}).get("incident_id") == incident_id and x.get("details", {}).get("action") == request.action for x in audit_log)
    if not approved:
        raise HTTPException(status_code=403, detail="Explicit human approval is required before execution")
    result = execute_approved_action(incident_id, request.action, engineer)
    with SessionLocal() as session:
        from .database import RemediationExecutionRecord
        session.add(RemediationExecutionRecord(incident_id=incident_id, action=request.action, engineer=engineer, status=result.get("status", "EXECUTED"), verification=json.dumps(result.get("verification", []))))
        session.commit()
    return result


@app.get("/api/v1/incidents/{incident_id}/remediation")
def incident_remediation(incident_id: str, engineer: str = Depends(current_engineer)):
    if not store.get(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    executions = [x for x in execution_log if x.get("incident_id") == incident_id]
    return {"incident_id": incident_id, "executions": executions, "latest": executions[-1] if executions else None}


@app.post("/api/v1/guardrails/check")
def guardrail_check(payload: dict, engineer: str = Depends(current_engineer)):
    return classify_action(payload.get("action", ""))


@app.get("/api/v1/metrics")
def metrics(engineer: str = Depends(current_engineer)):
    incident_count = len(store.incidents())
    action_count = len(execution_log)
    approvals = sum(1 for x in audit_log if x.get("event") == "HUMAN_APPROVAL" and x.get("details", {}).get("state") == "APPROVED")
    blocked = sum(1 for x in audit_log if x.get("event") == "HUMAN_APPROVAL" and x.get("details", {}).get("state") == "REJECTED")
    return {"active_incidents": incident_count, "clients_monitored": len(clients), "actions_executed": action_count, "human_approvals": approvals, "human_rejections": blocked, "audit_events": len(persisted_audits()), "uptime_status": "OPERATIONAL", "database": database_status(), "timestamp": datetime.now(timezone.utc).isoformat(), "severity_distribution": dict(Counter(e.severity.value for i in store.incidents() for e in store.get(i)))}


@app.get("/api/v1/audit")
def audit(engineer: str = Depends(current_engineer)):
    return list(reversed(persisted_audits()[-100:]))


from .client_gateway import authenticate_client


@app.post("/api/v1/client/events", response_model=IngestResponse)
def client_ingest(request: IngestRequest, http_request: Request):
    client_id = http_request.headers.get("X-TraceGaurd-Client-ID", "")
    if not client_id or client_id not in clients:
        raise HTTPException(status_code=401, detail="Valid X-TraceGaurd-Client-ID is required")
    authenticate_client(http_request, client_id)
    normalized = normalize_events(request.events)
    for event in normalized:
        event.metadata["client_id"] = client_id
        event.metadata["client_name"] = clients[client_id]["name"]
        if not event.metadata.get("tokens"):
            event.metadata["tokens"] = max(1, len(event.message) // 4)
    store.add_many(normalized)
    client = clients[client_id]
    client["last_seen"] = datetime.now(timezone.utc).isoformat()
    client["status"] = "MONITORING"
    client["incidents"] += len({event.incident_id for event in normalized})
    persist_client(client)
    record_audit("CLIENT_EVENTS_INGESTED", client_id, {"client_id": client_id, "events": len(normalized), "incidents": sorted({event.incident_id for event in normalized})})
    return IngestResponse(accepted=len(normalized), incident_ids=sorted({event.incident_id for event in normalized}))
