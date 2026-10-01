import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "engineer@tracegaurd.ai", "password": "ci-test-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_duplicate_client_registration_is_rejected():
    headers = auth_headers()
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "name": f"Duplicate Guard {suffix}",
        "environment": "production",
        "service": "shared-api",
        "website_url": f"https://duplicate-{suffix}.example.com",
        "health_path": "/",
    }
    first = client.post("/api/v1/clients", headers=headers, json=payload)
    assert first.status_code == 200
    second = client.post("/api/v1/clients", headers=headers, json=payload)
    assert second.status_code == 400


def test_client_incidents_and_scores_are_isolated():
    headers = auth_headers()
    suffix = uuid.uuid4().hex[:8]
    clients = []
    for name in (f"Isolation A {suffix}", f"Isolation B {suffix}"):
        response = client.post(
            "/api/v1/clients",
            headers=headers,
            json={
                "name": name,
                "environment": "production",
                "service": "shared-api",
                "website_url": f"https://{name.lower().replace(' ', '-')}.example.com",
                "health_path": "/",
            },
        )
        assert response.status_code == 200
        clients.append(response.json())

    listing = client.get("/api/v1/clients", headers=headers)
    assert listing.status_code == 200
    ids = [item["client_id"] for item in listing.json()]
    assert len(ids) == len(set(ids))
    assert sum(item["name"] == clients[0]["name"] for item in listing.json()) == 1
    assert sum(item["name"] == clients[1]["name"] for item in listing.json()) == 1

    incident_ids = []
    for item in clients:
        response = client.post(f"/api/v1/clients/{item['client_id']}/simulate-incident", headers=headers)
        assert response.status_code == 200
        incident_ids.append(response.json()["incident_ids"][0])

    incidents = client.get("/api/v1/incidents", headers=headers).json()
    scoped = {item["client_id"]: {item["incident_id"] for item in incidents if item["client_id"] == item["client_id"]} for item in clients}
    assert incident_ids[0] != incident_ids[1]
    assert incident_ids[0] in scoped[clients[0]["client_id"]]
    assert incident_ids[1] in scoped[clients[1]["client_id"]]

    for item in clients:
        score = client.get(f"/api/v1/clients/{item['client_id']}/score", headers=headers)
        assert score.status_code == 200
        body = score.json()
        assert body["client_id"] == item["client_id"]
        assert body["max_score"] == 85
        assert 0 <= body["score"] <= 85
        assert set(body["components"]) == {"logs", "deployments", "audits", "tokens"}
