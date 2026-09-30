import hashlib
import hmac
import os

from fastapi.testclient import TestClient

from app.main import app
from app.monitoring import clients

client = TestClient(app)


def login():
    response = client.post("/api/v1/auth/login", json={"email": os.getenv("DEMO_ENGINEER_EMAIL", "engineer@tracegaurd.ai"), "password": os.getenv("DEMO_ENGINEER_PASSWORD", "ci-test-password")})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_signed_client_ingestion(monkeypatch):
    headers = login()
    created = client.post("/api/v1/clients", headers=headers, json={"name": "Gateway Test", "environment": "staging", "service": "gateway-api"})
    assert created.status_code == 200
    client_id = created.json()["client_id"]
    secret = "test-client-secret"
    monkeypatch.setenv("TRACEGAURD_CLIENT_INGEST_SECRET", secret)
    signature = hmac.new(secret.encode(), client_id.encode(), hashlib.sha256).hexdigest()
    payload = {"events": [{"incident_id": "gateway-test-1", "timestamp": "2026-09-30T18:00:00Z", "source": "alert", "service": "gateway-api", "severity": "critical", "message": "HTTP 500 responses increased"}]}
    response = client.post("/api/v1/client/events", headers={"X-TraceGaurd-Client-ID": client_id, "X-TraceGaurd-Signature": signature}, json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    assert "gateway-test-1" in response.json()["incident_ids"]


def test_client_ingestion_rejects_invalid_signature(monkeypatch):
    login()
    client_id = next(iter(clients))
    monkeypatch.setenv("TRACEGAURD_CLIENT_INGEST_SECRET", "test-client-secret")
    payload = {"events": [{"incident_id": "gateway-test-2", "timestamp": "2026-09-30T18:00:00Z", "source": "alert", "service": "checkout-api", "severity": "warning", "message": "Timeout detected"}]}
    response = client.post("/api/v1/client/events", headers={"X-TraceGaurd-Client-ID": client_id, "X-TraceGaurd-Signature": "bad"}, json=payload)
    assert response.status_code == 401
