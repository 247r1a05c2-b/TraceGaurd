from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

clients: dict[str, dict[str, Any]] = {}
audit_log: list[dict[str, Any]] = []
execution_log: list[dict[str, Any]] = []


def register_client(name: str, environment: str, service: str) -> dict[str, Any]:
    client_id = f"client-{uuid4().hex[:8]}"
    client = {"client_id": client_id, "name": name, "environment": environment, "service": service, "status": "MONITORING", "last_seen": datetime.now(timezone.utc).isoformat(), "incidents": 0}
    clients[client_id] = client
    return client


def heartbeat(client_id: str) -> dict[str, Any]:
    if client_id not in clients:
        raise KeyError(client_id)
    clients[client_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
    clients[client_id]["status"] = "MONITORING"
    return clients[client_id]


def record_audit(event: str, actor: str, details: dict[str, Any]) -> None:
    audit_log.append({"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "actor": actor, "details": details})


def execute_approved_action(incident_id: str, action: str, actor: str) -> dict[str, Any]:
    allowed = {"Freeze further checkout deployments", "Inspect database pool saturation", "Compare current and previous checkout release", "Rollback checkout deployment", "Restart affected service"}
    if action not in allowed:
        raise ValueError("Action is not on the TraceGaurd execution allow-list")
    result = {"execution_id": f"exec-{uuid4().hex[:8]}", "incident_id": incident_id, "action": action, "status": "SIMULATED_SUCCESS", "actor": actor, "timestamp": datetime.now(timezone.utc).isoformat(), "message": "TraceGaurd executed the approved demo remediation workflow. Connect a signed production adapter before real mutations."}
    execution_log.append(result)
    record_audit("ACTION_EXECUTED", actor, result)
    return result


for name, environment, service in [("Acme Checkout", "production", "checkout-api"), ("FinServe Payments", "staging", "payments-api"), ("RetailHub Orders", "production", "orders-api")]:
    register_client(name, environment, service)
