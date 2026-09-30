from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_simulate_checkout():
    response = client.post("/api/v1/simulate/checkout")
    assert response.status_code == 200
    assert response.json()["accepted"] == 4


def test_incident_events_are_sorted():
    client.post("/api/v1/simulate/checkout")
    response = client.get("/api/v1/incidents/INC-1001/events")
    assert response.status_code == 200
    events = response.json()
    assert [event["source"] for event in events] == ["deployment", "alert", "log", "ticket"]


def test_unknown_scenario():
    response = client.post("/api/v1/simulate/unknown")
    assert response.status_code == 404
