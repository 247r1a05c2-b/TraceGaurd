from app.graph import run_graph


def test_graph_contains_multi_agent_trace_and_rag():
    events = [
        {"timestamp": "2026-09-30T10:00:00Z", "source": "deployment", "service": "checkout", "severity": "info", "message": "Deployment v2.8.1 completed successfully"},
        {"timestamp": "2026-09-30T10:01:00Z", "source": "alert", "service": "checkout", "severity": "critical", "message": "HTTP 500 error rate crossed 20%"},
        {"timestamp": "2026-09-30T10:02:00Z", "source": "log", "service": "database", "severity": "critical", "message": "Connection pool timeout detected"},
    ]
    result = run_graph(events)
    assert result["root_cause"]
    assert len(result["agent_trace"]) == 8
    assert len(result["rag_context"]) >= 4
    assert result["steps"] and len(result["steps"]) >= 4
    assert result["actions"]
    assert any(action.get("risk") == "APPROVAL" for action in result["actions"])
    assert result["risk"] == "APPROVAL_REQUIRED"
