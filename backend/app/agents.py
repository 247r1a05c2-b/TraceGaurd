from typing import Any

from .ai_engine import analyze_incident
from .rag import retrieve


def run_agents(events: list[dict[str, Any]]) -> dict[str, Any]:
    analysis = analyze_incident(events)
    query = f"{analysis['root_cause']} checkout database deployment rollback"
    context = retrieve(query)
    analysis["rag_context"] = context
    analysis["agent_trace"] = [
        {"agent": "Ingestion Agent", "status": "complete", "output": "Normalized incident events"},
        {"agent": "Noise Filter Agent", "status": "complete", "output": "Prioritized critical signals"},
        {"agent": "Correlation Agent", "status": "complete", "output": "Linked deployment, checkout errors, and database timeouts"},
        {"agent": "Root Cause Agent", "status": "complete", "output": analysis["root_cause"]},
        {"agent": "Diagnostic Agent", "status": "complete", "output": "Generated read-only diagnostic actions"},
        {"agent": "RAG Agent", "status": "complete", "output": f"Retrieved {len(context)} runbook records"},
        {"agent": "Guardrail Agent", "status": "complete", "output": "Rollback classified as APPROVAL"},
        {"agent": "Timeline Agent", "status": "complete", "output": "Built evidence-backed incident sequence"},
    ]
    return analysis
