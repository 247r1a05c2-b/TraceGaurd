from app.ai_engine import analyze_incident
from app.guardrails import classify_action


def test_analysis_explains_incident():
    events = [
        {"timestamp":"2026-09-30T10:00:00Z","source":"deployment","severity":"info","message":"Deployment v2.8.1 completed successfully","metadata":{"version":"v2.8.1"}},
        {"timestamp":"2026-09-30T10:01:00Z","source":"alert","severity":"critical","message":"HTTP 500 error rate crossed 20%","metadata":{}},
        {"timestamp":"2026-09-30T10:02:00Z","source":"log","severity":"critical","message":"Connection pool timeout detected","metadata":{}},
    ]
    result = analyze_incident(events)
    assert result["confidence"] > 0
    assert len(result["steps"]) >= 4
    assert result["risk"] == "APPROVAL_REQUIRED"


def test_unknown_action_is_blocked():
    assert classify_action("Delete production database")["risk"] == "BLOCKED"
