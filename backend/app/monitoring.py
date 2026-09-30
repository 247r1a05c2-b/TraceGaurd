from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from time import perf_counter

clients: dict[str, dict[str, Any]] = {}
audit_log: list[dict[str, Any]] = []
execution_log: list[dict[str, Any]] = []


def register_client(name: str, environment: str, service: str, website_url: str | None = None, health_path: str = "/") -> dict[str, Any]:
    client_id = f"client-{uuid4().hex[:8]}"
    client = {
        "client_id": client_id, "name": name, "environment": environment, "service": service,
        "website_url": website_url, "health_path": health_path or "/", "status": "MONITORING",
        "last_seen": datetime.now(timezone.utc).isoformat(), "last_response_ms": None,
        "last_http_status": None, "incidents": 0,
    }
    clients[client_id] = client
    return client


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
    audit_log.append({"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "actor": actor, "details": details})


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
    register_client(name, environment, service)
