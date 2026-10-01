from fastapi.testclient import TestClient

from app.main import app
from app.enterprise import cache, install_enterprise

install_enterprise(app)
client = TestClient(app)


def test_liveness_probe():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_probe():
    response = client.get("/health/ready")
    assert response.status_code in {200, 503}
    payload = response.json()
    assert "database" in payload.get("detail", payload)


def test_prometheus_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "tracegaurd_http_request_duration_seconds" in response.text


def test_enterprise_status():
    response = client.get("/api/v1/enterprise/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["scalability"]["horizontal_autoscaling"] is True
    assert payload["monitoring"]["prometheus"] is True


def test_cache_round_trip():
    cache.set("test:enterprise", {"ok": True}, ttl=10)
    assert cache.get("test:enterprise")["ok"] is True
