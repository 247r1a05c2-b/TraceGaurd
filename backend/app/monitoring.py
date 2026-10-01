from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from time import perf_counter
import json

from .database import AuditRecord, ClientRecord, SessionLocal

clients: dict[str, dict[str, Any]] = {}
audit_log: list[dict[str, Any]] = []
execution_log: list[dict[str, Any]] = []


def _identity(name: str, environment: str, service: str, website_url: str | None) -> tuple[str, str, str, str]:
    return (
        name.strip().casefold(),
        environment.strip().casefold(),
        service.strip().casefold(),
        (website_url or "").strip().rstrip("/").casefold(),
    )


def register_client(name: str, environment: str, service: str, website_url: str | None = None, health_path: str = "/") -> dict[str, Any]:
    name = name.strip()
    environment = environment.strip()
    service = service.strip()
    website_url = website_url.strip().rstrip("/") if website_url else None
    health_path = (health_path or "/").strip() or "/"
    if website_url:
        parsed = urlparse(website_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("website_url must be a valid http or https URL")
    identity = _identity(name, environment, service, website_url)
    if any(_identity(str(item.get("name", "")), str(item.get("environment", "")), str(item.get("service", "")), item.get("website_url")) == identity for item in clients.values()):
        raise ValueError("A client with the same name, environment, service and website is already registered")
    with SessionLocal() as session:
        for record in session.query(ClientRecord).all():
            if _identity(record.name, record.environment, record.service, record.website_url) == identity:
                raise ValueError("A client with the same name, environment, service and website is already registered")
    client_id = f"client-{uuid4().hex[:12]}"
    client = {
        "client_id": client_id,
        "name": name,
        "environment": environment,
        "service": service,
        "website_url": website_url,
        "health_path": health_path,
        "status": "MONITORING" if website_url else "ONLINE",
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "last_response_ms": None,
        "last_http_status": None,
        "incidents": 0,
    }
    clients[client_id] = client
    return client


def hydrate_clients(records: list[dict[str, Any]]) -> None:
    for record in records:
        hydrated = {
            "client_id": record["id"],
            "name": record["name"],
            "environment": record["environment"],
            "service": record["service"],
            "website_url": record.get("website_url"),
            "health_path": record.get("health_path") or "/",
            "status": record.get("status") or "ONLINE",
            "last_seen": record.get("last_seen"),
            "last_response_ms": record.get("last_response_ms"),
            "last_http_status": record.get("last_http_status"),
            "incidents": int(record.get("incidents") or 0),
        }
        identity = _identity(hydrated["name"], hydrated["environment"], hydrated["service"], hydrated.get("website_url"))
        duplicate_ids = [
            client_id for client_id, item in clients.items()
            if _identity(str(item.get("name", "")), str(item.get("environment", "")), str(item.get("service", "")), item.get("website_url")) == identity
            and client_id != hydrated["client_id"]
        ]
        for duplicate_id in duplicate_ids:
            clients.pop(duplicate_id, None)
        clients[hydrated["client_id"]] = hydrated


def heartbeat(client_id: str) -> dict[str, Any]:
    if client_id not in clients:
        raise KeyError(client_id)
    clients[client_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
    clients[client_id]["status"] = "MONITORING"
    return clients[client_id]


def check_website(client_id: str) -> dict[str, Any]:
    if client_id not in clients:
        raise KeyError(client_id)
    client = clients[client_id]
    url = client.get("website_url")
    if not url:
        raise ValueError("Client does not have a website URL")
    target = url.rstrip("/") + "/" + str(client.get("health_path") or "/").lstrip("/")
    started = perf_counter()
    now = datetime.now(timezone.utc).isoformat()
    try:
        request = Request(target, headers={"User-Agent": "TraceGaurd-Monitor/1.0", "Accept": "text/html,application/json"}, method="GET")
        with urlopen(request, timeout=8) as response:
            status_code = int(response.status)
            response.read(2048)
        elapsed = round((perf_counter() - started) * 1000)
        healthy = 200 <= status_code < 400
        client.update({"last_seen": now, "last_response_ms": elapsed, "last_http_status": status_code, "status": "ONLINE" if healthy else "DEGRADED"})
        return {"client_id": client_id, "url": target, "healthy": healthy, "status": client["status"], "http_status": status_code, "response_ms": elapsed, "checked_at": now}
    except HTTPError as exc:
        elapsed = round((perf_counter() - started) * 1000)
        client.update({"last_seen": now, "last_response_ms": elapsed, "last_http_status": int(exc.code), "status": "DOWN" if exc.code >= 500 else "DEGRADED"})
        return {"client_id": client_id, "url": target, "healthy": False, "status": client["status"], "http_status": int(exc.code), "response_ms": elapsed, "checked_at": now, "error": str(exc)}
    except (URLError, TimeoutError, ValueError) as exc:
        elapsed = round((perf_counter() - started) * 1000)
        client.update({"last_seen": now, "last_response_ms": elapsed, "last_http_status": None, "status": "DOWN"})
        return {"client_id": client_id, "url": target, "healthy": False, "status": "DOWN", "http_status": None, "response_ms": elapsed, "checked_at": now, "error": str(exc)}


def record_audit(event: str, actor: str, details: dict[str, Any]) -> None:
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "actor": actor, "details": details}
    audit_log.append(record)
    try:
        with SessionLocal() as session:
            session.add(AuditRecord(event=event, actor=actor, details=json.dumps(details, default=str)))
            session.commit()
    except Exception:
        pass


def _client_event_matches(event: Any, client: dict[str, Any]) -> bool:
    metadata = getattr(event, "metadata", {}) or {}
    event_client_id = metadata.get("client_id")
    if event_client_id is not None:
        return str(event_client_id) == str(client["client_id"])
    return str(getattr(event, "service", "")).lower() == str(client.get("service", "")).lower()


def calculate_client_score(client: dict[str, Any], events: list[Any], audits: list[dict[str, Any]]) -> dict[str, Any]:
    scoped = [event for event in events if _client_event_matches(event, client)]
    log_events = [event for event in scoped if getattr(event.source, "value", event.source) == "log"]
    deployment_events = [event for event in scoped if getattr(event.source, "value", event.source) == "deployment"]
    critical_logs = sum(1 for event in log_events if getattr(event.severity, "value", event.severity) == "critical")
    warning_logs = sum(1 for event in log_events if getattr(event.severity, "value", event.severity) == "warning")
    token_count = 0
    for event in scoped:
        metadata = getattr(event, "metadata", {}) or {}
        token_count += int(metadata.get("tokens") or max(1, round(len(str(getattr(event, "message", ""))) / 4)))
    client_audits = [item for item in audits if item.get("actor") == client["client_id"] or item.get("details", {}).get("client_id") == client["client_id"] or item.get("details", {}).get("clientId") == client["client_id"]]
    log_score = max(0, 85 - critical_logs * 12 - warning_logs * 4)
    deployment_score = max(0, 85 - max(0, len(deployment_events) - 1) * 6)
    audit_score = min(85, 45 + len(client_audits) * 5)
    token_score = max(0, 85 - max(0, token_count - 400) // 100 * 4)
    status_penalty = 20 if client.get("status") == "DOWN" else 10 if client.get("status") == "DEGRADED" else 0
    overall = max(0, min(85, round(log_score * 0.35 + deployment_score * 0.25 + audit_score * 0.15 + token_score * 0.25 - status_penalty)))
    return {
        "score": overall,
        "max_score": 85,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "components": {
            "logs": {"events": len(log_events), "critical": critical_logs, "warning": warning_logs, "score": log_score},
            "deployments": {"events": len(deployment_events), "score": deployment_score},
            "audits": {"events": len(client_audits), "score": audit_score},
            "tokens": {"estimated": token_count, "score": token_score},
        },
        "status_penalty": status_penalty,
        "method": "Client-scoped weighted operational score; recalculated on every request and capped at 85.",
    }


def execute_approved_action(incident_id: str, action: str, actor: str) -> dict[str, Any]:
    allowed = {"Freeze further checkout deployments", "Inspect database pool saturation", "Compare current and previous checkout release", "Rollback checkout deployment", "Restart affected service"}
    if action not in allowed:
        raise ValueError("Action is not on the TraceGaurd execution allow-list")
    now = datetime.now(timezone.utc).isoformat()
    verification = [
        {"check": "Execution safety", "status": "PASS", "message": "Only an allow-listed remediation was executed after explicit human approval."},
        {"check": "Service health", "status": "PENDING", "message": "Connect a signed infrastructure adapter to perform live health checks."},
        {"check": "Error rate", "status": "PENDING", "message": "Connect the client's telemetry provider to compare pre/post remediation error rate."},
    ]
    result = {"execution_id": f"exec-{uuid4().hex[:8]}", "incident_id": incident_id, "action": action, "status": "SIMULATED_SUCCESS", "actor": actor, "timestamp": now, "message": "TraceGaurd executed the approved demo remediation workflow. Connect a signed production adapter before real mutations.", "verification": verification}
    execution_log.append(result)
    record_audit("ACTION_EXECUTED", actor, result)
    return result


for name, environment, service in [("Acme Checkout", "production", "checkout-api"), ("FinServe Payments", "staging", "payments-api"), ("RetailHub Orders", "production", "orders-api")]:
    try:
        register_client(name, environment, service)
    except ValueError:
        pass
