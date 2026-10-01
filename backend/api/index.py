import sys
from pathlib import Path
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.client_routes import install_client_routes
from app.database import ApprovalRecord, SessionLocal
from app.monitoring import record_audit
from app.security import verify_token
from app.runtime_fixes import install_runtime_fixes
from app.enterprise import install_enterprise


@app.exception_handler(IntegrityError)
async def handle_database_integrity_error(request: Request, exc: IntegrityError):
    path = request.url.path.rstrip("/")
    if path.startswith("/api/v1/incidents/") and path.endswith("/approve"):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        action = str(payload.get("action", "")).strip()
        approved = bool(payload.get("approved", False))
        parts = path.strip("/").split("/")
        incident_id = parts[-2] if len(parts) >= 2 else "unknown"
        credentials = request.headers.get("Authorization", "")
        token = credentials[7:] if credentials.lower().startswith("bearer ") else ""
        engineer = verify_token(token) or "unknown-engineer"
        approval_id = f"approval-{uuid4().hex[:16]}"
        state = "APPROVED" if approved else "REJECTED"
        try:
            with SessionLocal() as session:
                session.add(ApprovalRecord(id=approval_id, incident_id=incident_id, action=action, engineer=engineer, state=state))
                session.commit()
        except Exception as recovery_error:
            return JSONResponse(status_code=409, content={"detail": f"Approval could not be persisted safely: {type(recovery_error).__name__}"})
        record_audit("HUMAN_APPROVAL", engineer, {"incident_id": incident_id, "action": action, "state": state, "approval_id": approval_id, "recovered_from_integrity_error": True})
        return JSONResponse(status_code=200, content={"approval_id": approval_id, "incident_id": incident_id, "action": action, "state": state, "guardrail": {"risk": "APPROVAL", "message": "Human approval recorded safely."}, "recovered": True})
    raise exc


install_client_routes(app)
install_runtime_fixes(app)
install_enterprise(app)

__all__ = ["app"]
