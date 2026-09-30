import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login():
    response = client.post("/api/v1/auth/login", json={"email": os.getenv("DEMO_ENGINEER_EMAIL", "engineer@tracegaurd.ai"), "password": os.getenv("DEMO_ENGINEER_PASSWORD", "ci-test-password")})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_and_me():
    headers = login()
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "SOFTWARE_ENGINEER"


def test_protected_incidents_require_login():
    assert client.get("/api/v1/incidents").status_code == 401


def test_incident_analysis_and_metrics():
    headers = login()
    simulated = client.post("/api/v1/simulate/checkout", headers=headers)
    assert simulated.status_code == 200
    incident_id = simulated.json()["incident_ids"][0]
    analysis = client.get(f"/api/v1/incidents/{incident_id}/analysis", headers=headers)
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["root_cause"]
    assert 0 <= body["confidence"] <= 100
    assert len(body["agent_trace"]) == 8
    assert "evaluation" in body
    assert any(a["risk"] == "APPROVAL" for a in body["actions"])
    metrics = client.get("/api/v1/metrics", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["clients_monitored"] >= 3


def test_human_approval_is_required_before_execution():
    headers = login()
    simulated = client.post("/api/v1/simulate/checkout", headers=headers)
    incident_id = simulated.json()["incident_ids"][0]
    action = "Rollback checkout deployment"
    denied = client.post(f"/api/v1/incidents/{incident_id}/execute", headers=headers, json={"action": action, "approval_id": "missing"})
    assert denied.status_code == 403
    approval = client.post(f"/api/v1/incidents/{incident_id}/approve", headers=headers, json={"action": action, "approved": True})
    assert approval.status_code == 200
    execution = client.post(f"/api/v1/incidents/{incident_id}/execute", headers=headers, json={"action": action, "approval_id": approval.json()["approval_id"]})
    assert execution.status_code == 200
    assert execution.json()["status"] == "SIMULATED_SUCCESS"
