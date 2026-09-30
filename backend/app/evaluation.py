from typing import Any


def build_evaluation(analysis: dict[str, Any]) -> dict[str, Any]:
    trace = analysis.get("agent_trace", [])
    agent_metrics = []
    for item in trace:
        agent_metrics.append({
            "agent": item.get("agent", "Unknown Agent"),
            "confidence": int(item.get("confidence", 0)),
            "metric": item.get("metric", "execution_quality"),
            "basis": item.get("basis", "Observed workflow output"),
            "status": item.get("status", "complete"),
        })
    scores = [x["confidence"] for x in agent_metrics]
    evidence_count = len(analysis.get("evidence", []))
    rag_count = len(analysis.get("rag_context", []))
    actions = analysis.get("actions", [])
    approval_required = sum(1 for a in actions if a.get("risk") == "APPROVAL")
    blocked = sum(1 for a in actions if a.get("risk") == "BLOCKED")
    overall = round(sum(scores) / max(1, len(scores)))
    return {
        "overall_pipeline_confidence": overall,
        "root_cause_confidence": int(analysis.get("confidence", 0)),
        "agent_metrics": agent_metrics,
        "evidence_coverage": min(100, evidence_count * 15 + rag_count * 10),
        "rag_retrieval_coverage": min(100, rag_count * 20),
        "diagnosis_coverage": min(100, len(analysis.get("steps", [])) * 20),
        "safety_gate_score": 100 if blocked == 0 else max(0, 100 - blocked * 25),
        "human_control": 100 if approval_required or not actions else 90,
        "llm_enabled": bool(analysis.get("llm_used", False)),
        "distinctive_capabilities": [
            "Evidence-weighted root-cause confidence instead of an unexplained AI percentage",
            "Per-agent evaluation scores with an explicit measurement basis",
            "RAG retrieval evidence linked to the diagnosis",
            "Guardrail-first remediation with mandatory human approval for risky actions",
            "Controlled remediation plus post-action verification and audit trail",
            "Deterministic safety fallback when the external LLM is unavailable",
        ],
        "comparison_note": "These are TraceGaurd product capabilities, not a benchmark ranking against named products. Confidence values are evidence-weighted estimates, not ground-truth accuracy.",
    }
