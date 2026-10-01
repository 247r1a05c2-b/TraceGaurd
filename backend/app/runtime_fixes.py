import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, HTTPException

from .database import ClientRecord, IncidentRecord, SessionLocal
from .main import current_engineer
from .models import IncidentEvent, IngestResponse, Severity
from .monitoring import check_website, clients, record_audit
from .normalizer import normalize_events
from .simulator import generate_scenario
from .store import store


def _recent_duplicate_web_incident(client_id: str, client_name: str) -> str | None:
    now = datetime.now(timezone.utc)
    prefix = f"{client_name} website health check failed"
    for incident_id in store.incidents():
        for event in store.get(incident_id):
            metadata = event.metadata or {}
            source = getattr(event.source, "value", event.source)
            if metadata.get("client_id") != client_id or source != "alert":
                continue
            if not event.message.startswith(prefix):
                continue
            try:
                event_time = event.timestamp
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                if 0 <= (now - event_time).total_seconds() <= 15 * 60:
                    return incident_id
            except Exception:
                continue
    return None


def _safe_demo_checkout(engineer: str = Depends(current_engineer)):
    for _ in range(5):
        events = normalize_events(generate_scenario("checkout"))
        incident_id = events[0].incident_id if events else None
        if not incident_id:
            continue
        with SessionLocal() as session:
            if session.get(IncidentRecord, incident_id) is not None:
                continue
        if store.get(incident_id):
            continue
        store.add_many(events)
        record_audit("INCIDENT_INGESTED", engineer, {"scenario": "checkout", "events": len(events), "incident_id": incident_id})
        return IngestResponse(accepted=len(events), incident_ids=[incident_id])
    raise HTTPException(status_code=503, detail="Could not allocate a unique RCA demo incident")


def _safe_client_check(client_id: str, engineer: str = Depends(current_engineer)):
    try:
        result = check_website(client_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Client not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    client = clients[client_id]
    with SessionLocal() as session:
        record = session.get(ClientRecord, client_id)
        if record is not None:
            record.status = client.get("status", record.status)
            record.last_seen = datetime.fromisoformat(client["last_seen"]) if client.get("last_seen") else None
            record.last_response_ms = client.get("last_response_ms")
            record.last_http_status = client.get("last_http_status")
            session.commit()
    record_audit("WEBSITE_HEALTH_CHECK", engineer, result)

    if not result["healthy"]:
        duplicate_id = _recent_duplicate_web_incident(client_id, client["name"])
        if duplicate_id:
            result["incident_id"] = duplicate_id
            result["deduplicated"] = True
            result["message"] = "Existing matching incident reused; duplicate incident suppressed."
        else:
            incident_id = f"WEB-{uuid4().hex[:12].upper()}"
            status_text = result.get("http_status") or "NO_RESPONSE"
            error_text = result.get("error", "unhealthy response")
            event = IncidentEvent(
                incident_id=incident_id,
                source="alert",
                service=client["service"],
                severity=Severity.critical if result.get("status") == "DOWN" else Severity.warning,
                message=f"{client['name']} website health check failed for {result['url']}: status={status_text}; response_ms={result['response_ms']}; error={error_text}",
                metadata={
                    "client_id": client_id,
                    "client_name": client["name"],
                    "website_url": result["url"],
                    "http_status": result.get("http_status"),
                    "response_ms": result["response_ms"],
                    "tokens": max(1, len(str(error_text)) // 4),
                },
            )
            store.add_many([event])
            client["incidents"] += 1
            with SessionLocal() as session:
                record = session.get(ClientRecord, client_id)
                if record is not None:
                    record.incidents = client["incidents"]
                    session.commit()
            record_audit("CLIENT_INCIDENT_CREATED", client_id, {"client_id": client_id, "incident_id": incident_id, "reason": event.message})
            result["incident_id"] = incident_id
            result["deduplicated"] = False

    return result


def _patch_ai_fallbacks():
    try:
        from . import external_rag, graph as graph_module, rag as rag_module

        original_llm = graph_module._gemini_json
        original_external = external_rag.retrieve_external

        def llm_with_fallback(prompt):
            result = original_llm(prompt)
            if result is not None:
                return result
            old = os.getenv("GEMINI_MODEL")
            os.environ["GEMINI_MODEL"] = "gemini-flash-latest"
            try:
                return original_llm(prompt)
            finally:
                if old is None:
                    os.environ.pop("GEMINI_MODEL", None)
                else:
                    os.environ["GEMINI_MODEL"] = old

        def external_with_fallback(query, top_k=4):
            result = original_external(query, top_k=top_k)
            if result:
                return result
            old = os.getenv("GEMINI_MODEL")
            os.environ["GEMINI_MODEL"] = "gemini-flash-latest"
            try:
                return original_external(query, top_k=top_k)
            finally:
                if old is None:
                    os.environ.pop("GEMINI_MODEL", None)
                else:
                    os.environ["GEMINI_MODEL"] = old

        graph_module._gemini_json = llm_with_fallback
        external_rag.retrieve_external = external_with_fallback
        rag_module.retrieve_external = external_with_fallback
        graph_module.retrieve = rag_module.retrieve
    except Exception:
        pass


def install_runtime_fixes(app):
    _patch_ai_fallbacks()
    for route in app.routes:
        methods = getattr(route, "methods", set())
        if route.path == "/api/v1/simulate/checkout" and "POST" in methods:
            route.endpoint = _safe_demo_checkout
            route.dependant.call = _safe_demo_checkout
        elif route.path == "/api/v1/clients/{client_id}/check" and "POST" in methods:
            route.endpoint = _safe_client_check
            route.dependant.call = _safe_client_check
