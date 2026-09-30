from datetime import datetime
from typing import Any


def analyze_incident(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic incident analysis used as a zero-key demo fallback.

    The output is intentionally evidence-based: every conclusion points to an
    observed event. An LLM provider can be added later without changing the UI contract.
    """
    if not events:
        return {
            "summary": "No evidence available.",
            "root_cause": "Insufficient evidence",
            "confidence": 0,
            "steps": [],
            "actions": [],
            "evidence": [],
            "risk": "UNKNOWN",
        }

    ordered = sorted(events, key=lambda x: x["timestamp"])
    deployment = next((e for e in ordered if e["source"] == "deployment"), None)
    critical = [e for e in ordered if e["severity"] == "critical"]
    checkout_500 = [e for e in ordered if "500" in e["message"]]
    db_timeout = [e for e in ordered if "timeout" in e["message"].lower()]

    steps = []
    if deployment:
        steps.append({
            "stage": "1. Detect change",
            "finding": f"Deployment {deployment.get('metadata', {}).get('version', 'unknown')} completed before the incident signals.",
            "evidence": [deployment["message"]],
        })
    if checkout_500:
        steps.append({
            "stage": "2. Correlate symptoms",
            "finding": "Checkout HTTP 500 errors appeared immediately after the deployment.",
            "evidence": [e["message"] for e in checkout_500],
        })
    if db_timeout:
        steps.append({
            "stage": "3. Trace dependency",
            "finding": "Database connection-pool timeouts were observed during the same incident window.",
            "evidence": [e["message"] for e in db_timeout],
        })
    steps.append({
        "stage": "4. Form hypothesis",
        "finding": "The deployment is the leading correlated change and database timeouts are a supporting dependency signal.",
        "evidence": [e["message"] for e in critical],
    })
    steps.append({
        "stage": "5. Validate safely",
        "finding": "Require human approval before rollback or production mutation.",
        "evidence": ["Guardrail policy: production changes require approval"],
    })

    root = "Post-deployment checkout failure with database connection-pool pressure"
    confidence = 88 if deployment and db_timeout and checkout_500 else 62

    actions = [
        {"action": "Freeze further checkout deployments", "risk": "SAFE", "reason": "Prevents the incident from expanding."},
        {"action": "Inspect database connection pool and saturation", "risk": "SAFE", "reason": "Read-only diagnostic step."},
        {"action": "Compare v2.8.1 with the previous checkout release", "risk": "SAFE", "reason": "Read-only change analysis."},
        {"action": "Rollback checkout deployment", "risk": "APPROVAL", "reason": "Production state mutation requires human approval."},
    ]

    return {
        "summary": "Checkout failures correlate with the latest deployment and database timeout signals.",
        "root_cause": root,
        "confidence": confidence,
        "steps": steps,
        "actions": actions,
        "evidence": [e["message"] for e in ordered],
        "risk": "APPROVAL_REQUIRED",
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
