from fastapi.testclient import TestClient

from app.database import SessionLocal, SessionRecord, UserRecord, database_status
from app.main import app

client = TestClient(app)


def test_database_is_initialized():
    status = database_status()
    assert status["status"] == "CONNECTED"
    assert "users" in status["tables"]
    assert "auth_sessions" in status["tables"]
    assert "incident_events" in status["tables"]


def test_login_creates_database_session():
    response = client.post("/api/v1/auth/login", json={"email": "engineer@tracegaurd.ai", "password": "ci-test-password"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "SOFTWARE_ENGINEER"
    with SessionLocal() as session:
        user = session.get(UserRecord, "engineer@tracegaurd.ai")
        saved = session.query(SessionRecord).filter(SessionRecord.email == "engineer@tracegaurd.ai").count()
        assert user is not None
        assert user.password_hash
        assert saved >= 1


def test_invalid_password_is_rejected():
    response = client.post("/api/v1/auth/login", json={"email": "engineer@tracegaurd.ai", "password": "definitely-wrong"})
    assert response.status_code == 401
