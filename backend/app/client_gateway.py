import hashlib
import hmac
import os

from fastapi import HTTPException, Request


def authenticate_client(request: Request, client_id: str) -> None:
    secret = os.getenv("TRACEGAURD_CLIENT_INGEST_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Client ingestion is not configured")
    signature = request.headers.get("X-TraceGaurd-Signature", "")
    message = client_id.encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid client signature")
