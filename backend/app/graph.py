import os
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from .guardrails import classify_action
from .rag import retrieve


class RootCauseResult(BaseModel):
    root_cause: str
    confidence: int = Field(ge=0, le=100)
    summary: str
    evidence: list[str]
    hypothesis: str


class DiagnosticResult(BaseModel):
    steps: list[dict[str, Any]]
    actions: list[dict[str, Any]]


class IncidentState(TypedDict, total=False):
    events: list[dict[str, Any]]
    filtered_events: list[dict[str, Any]]
    correlations: list[dict[str, Any]]
    rag_context: list[dict[str, Any]]
    root_cause: str
    confidence: int
    summary: str
    hypothesis: str
    evidence: list[str]
    steps: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    timeline: list[dict[str, Any]]
    risk: str
    agent_trace: list[dict[str, Any]]
    llm_used: bool
    generated_at: str


def _trace(state: IncidentState, agent: str, output: str, score: int, metric: str, basis: str):
    return [*state.get("agent_trace", []), {"agent": agent, "status": "complete", "output": output, "confidence": max(0, min(100, int(score))), "metric": metric, "basis": basis}]


def _llm():
    if not os.getenv("OPENAI_API_KEY"):
        return None
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)


def ingestion_node(state: IncidentState):
    events = sorted(state.get("events", []), key=lambda e: e.get("timestamp", ""))
    valid = sum(1 for e in events if e.get("timestamp") and e.get("service") and e.get("message"))
    score = round(100 * valid / max(1, len(events)))
    return {"filtered_events": events, "agent_trace": _trace(state, "Ingestion Agent", f"Normalized {len(events)} events", score, "data_quality", f"{valid}/{len(events)} events contain timestamp, service and message")}


def noise_filter_node(state: IncidentState):
    events = state.get("filtered_events", [])
    critical = [e for e in events if e.get("severity") == "critical"]
    warning = [e for e in events if e.get("severity") == "warning"]
    selected = sorted(critical + warning + [e for e in events if e.get("severity") == "info"], key=lambda e: e.get("timestamp", ""))
    signal_ratio = round(100 * len(critical + warning) / max(1, len(events)))
    score = min(98, 70 + signal_ratio // 3)
    return {"filtered_events": selected, "agent_trace": _trace(state, "Noise Filter Agent", f"Prioritized {len(critical)} critical and {len(warning)} warning signals", score, "signal_quality", f"Severity-aware prioritization retained {len(selected)}/{len(events)} signals")}


def correlation_node(state: IncidentState):
    events = state.get("filtered_events", [])
    deployments = [e for e in events if e.get("source") == "deployment"]
    failures = [e for e in events if "500" in e.get("message", "") or "timeout" in e.get("message", "").lower()]
    correlations = []
    for deployment in deployments:
        related = [e for e in failures if e.get("timestamp", "") >= deployment.get("timestamp", "")]
        correlations.append({"change": deployment.get("message", ""), "related_failures": [e.get("message", "") for e in related], "service": deployment.get("service", "unknown")})
    if not correlations and failures:
        correlations.append({"change": "No deployment change detected", "related_failures": [e.get("message", "") for e in failures], "service": failures[0].get("service", "unknown")})
    linked = sum(len(c.get("related_failures", [])) for c in correlations)
    score = min(99, 50 + linked * 8 + len(correlations) * 8)
    return {"correlations": correlations, "agent_trace": _trace(state, "Correlation Agent", f"Linked {len(correlations)} change-to-failure relationships", score, "correlation_strength", f"{linked} failure signals linked to {len(correlations)} causal-change candidates")}


def rag_node(state: IncidentState):
    events = state.get("filtered_events", [])
    query = " ".join(e.get("message", "") for e in events[:12]) + " " + " ".join(c.get("change", "") for c in state.get("correlations", []))
    context = retrieve(query, top_k=5)
    scores = [float(d.get("score", 0)) for d in context]
    score = round(100 * sum(scores) / max(1, len(scores))) if scores else 0
    return {"rag_context": context, "agent_trace": _trace(state, "RAG Agent", f"Retrieved {len(context)} evidence records", score, "retrieval_relevance", f"Mean retrieval relevance across {len(context)} records")}


def _fallback_root_cause(state: IncidentState):
    events = state.get("filtered_events", [])
    deployment = next((e for e in events if e.get("source") == "deployment"), None)
    timeout = any("timeout" in e.get("message", "").lower() for e in events)
    five_hundred = any("500" in e.get("message", "") for e in events)
    if deployment and timeout and five_hundred:
        root, confidence = "Post-deployment checkout failure with database connection-pool pressure", 91
        summary = "A checkout deployment is temporally correlated with HTTP 500 failures and database connection-pool timeouts."
        hypothesis = "The deployment likely introduced or exposed a checkout path that increases database connection pressure."
    elif deployment and five_hundred:
        root, confidence = "Post-deployment checkout application failure", 78
        summary = "Checkout failures follow the latest deployment and are concentrated around the changed service."
        hypothesis = "The recent deployment is the strongest observed change correlated with the failure."
    elif timeout:
        root, confidence = "Database connection-pool saturation", 73
        summary = "Database timeout signals are the strongest repeated failure pattern."
        hypothesis = "Connection-pool pressure is likely contributing to request failures."
    else:
        root, confidence = "Insufficient evidence for a single root cause", 45
        summary = "The incident contains symptoms but not enough correlated evidence for a strong root-cause claim."
        hypothesis = "Collect additional logs, deployment history, and dependency metrics before changing production state."
    evidence = [e.get("message", "") for e in events if e.get("severity") in {"critical", "warning"}][:6]
    return RootCauseResult(root_cause=root, confidence=confidence, summary=summary, evidence=evidence, hypothesis=hypothesis)


def root_cause_node(state: IncidentState):
    llm = _llm()
    result = None
    llm_used = False
    if llm:
        try:
            structured = llm.with_structured_output(RootCauseResult)
            evidence = "\n".join(f"- {e.get('timestamp')} | {e.get('service')} | {e.get('severity')} | {e.get('message')}" for e in state.get("filtered_events", []))
            rag = "\n".join(f"- {d['title']}: {d['content']}" for d in state.get("rag_context", []))
            prompt = f"""You are the Root Cause Agent for an SRE incident. Determine the most defensible root-cause hypothesis from observed evidence. Do not invent facts. Retrieved knowledge is supporting context, not incident evidence. State uncertainty when evidence is incomplete.

OBSERVED EVENTS:
{evidence}

CORRELATIONS:
{state.get('correlations', [])}

RETRIEVED KNOWLEDGE:
{rag}"""
            result = structured.invoke(prompt)
            llm_used = True
        except Exception:
            result = None
    result = result or _fallback_root_cause(state)
    return {"root_cause": result.root_cause, "confidence": result.confidence, "summary": result.summary, "hypothesis": result.hypothesis, "evidence": result.evidence, "llm_used": llm_used, "agent_trace": _trace(state, "Root Cause Agent", result.root_cause, result.confidence, "root_cause_confidence", f"Evidence-supported hypothesis; LLM={llm_used}")}


def diagnostic_node(state: IncidentState):
    llm = _llm()
    steps, actions = [], []
    if llm:
        try:
            structured = llm.with_structured_output(DiagnosticResult)
            events = "\n".join(f"{e.get('timestamp')} | {e.get('service')} | {e.get('message')}" for e in state.get("filtered_events", []))
            rag = "\n".join(f"{d['title']}: {d['content']}" for d in state.get("rag_context", []))
            prompt = f"""You are the Diagnostic Agent. Create a safe, evidence-backed investigation plan. Prefer read-only validation. Never make destructive production changes automatically. Return 4-6 ordered diagnosis steps and 3-5 recommended actions. Each step needs stage, finding, evidence. Each action needs action, risk, reason.

ROOT-CAUSE HYPOTHESIS: {state.get('root_cause')}
SUMMARY: {state.get('summary')}
EVENTS:
{events}
RUNBOOKS:
{rag}"""
            result = structured.invoke(prompt)
            steps, actions = result.steps, result.actions
        except Exception:
            pass
    if not steps:
        steps = [
            {"stage": "1. Confirm change window", "finding": "Compare the deployment timestamp with the first failure signal.", "evidence": [c.get("change", "") for c in state.get("correlations", [])]},
            {"stage": "2. Validate symptom pattern", "finding": "Check whether HTTP 500s cluster on the affected service and endpoint.", "evidence": state.get("evidence", [])[:3]},
            {"stage": "3. Trace dependency pressure", "finding": "Inspect database connection-pool usage, saturation and timeout rate.", "evidence": [e.get("message", "") for e in state.get("filtered_events", []) if "timeout" in e.get("message", "").lower()]},
            {"stage": "4. Compare release behavior", "finding": "Diff the current release against the previous known-good version.", "evidence": [c.get("change", "") for c in state.get("correlations", [])]},
            {"stage": "5. Validate remediation", "finding": "Use a canary or rollback only after evidence supports the hypothesis and a human approves the production mutation.", "evidence": [d.get("content", "") for d in state.get("rag_context", []) if "rollback" in d.get("title", "").lower()]},
        ]
    if not actions:
        actions = [
            {"action": "Freeze further checkout deployments", "risk": "SAFE", "reason": "Limits the incident blast radius without mutating production state."},
            {"action": "Inspect database pool saturation", "risk": "SAFE", "reason": "Read-only diagnostic validation."},
            {"action": "Compare current and previous checkout release", "risk": "SAFE", "reason": "Read-only change analysis."},
            {"action": "Rollback checkout deployment", "risk": "APPROVAL", "reason": "Production mutation requires explicit human approval."},
        ]
    coverage = min(100, round((len(steps) / 5) * 100))
    return {"steps": steps, "actions": actions, "agent_trace": _trace(state, "Diagnostic Agent", f"Generated {len(steps)} ordered diagnosis steps", coverage, "diagnostic_coverage", f"{len(steps)} ordered investigation steps with evidence fields")}


def guardrail_node(state: IncidentState):
    actions = []
    for action in state.get("actions", []):
        checked = classify_action(action.get("action", ""))
        actions.append({**action, **checked})
    blocked = sum(1 for a in actions if a.get("risk") == "BLOCKED")
    approval = sum(1 for a in actions if a.get("risk") == "APPROVAL")
    score = 100 if blocked == 0 else max(60, 100 - blocked * 20)
    risk = "APPROVAL_REQUIRED" if approval or blocked else "SAFE"
    return {"actions": actions, "risk": risk, "agent_trace": _trace(state, "Guardrail Agent", f"Classified {len(actions)} actions; {approval} require human approval", score, "safety_gate", f"Blocked={blocked}, approval_required={approval}, safe={len(actions)-blocked-approval}")}


def timeline_node(state: IncidentState):
    timeline = [{"timestamp": e.get("timestamp"), "source": e.get("source"), "service": e.get("service"), "severity": e.get("severity"), "message": e.get("message")} for e in state.get("filtered_events", [])]
    score = round(100 * len(timeline) / max(1, len(state.get("events", []))))
    return {"timeline": timeline, "generated_at": datetime.now(timezone.utc).isoformat(), "agent_trace": _trace(state, "Timeline Agent", f"Built {len(timeline)} chronological evidence records", score, "timeline_completeness", f"{len(timeline)}/{len(state.get('events', []))} source events represented")}


def build_graph():
    graph = StateGraph(IncidentState)
    for name, node in [("ingestion", ingestion_node), ("noise_filter", noise_filter_node), ("correlation", correlation_node), ("rag", rag_node), ("root_cause", root_cause_node), ("diagnostic", diagnostic_node), ("guardrail", guardrail_node), ("timeline", timeline_node)]:
        graph.add_node(name, node)
    graph.add_edge(START, "ingestion")
    graph.add_edge("ingestion", "noise_filter")
    graph.add_edge("noise_filter", "correlation")
    graph.add_edge("correlation", "rag")
    graph.add_edge("rag", "root_cause")
    graph.add_edge("root_cause", "diagnostic")
    graph.add_edge("diagnostic", "guardrail")
    graph.add_edge("guardrail", "timeline")
    graph.add_edge("timeline", END)
    return graph.compile()


incident_graph = build_graph()


def run_graph(events: list[dict[str, Any]]):
    result = incident_graph.invoke({"events": events, "agent_trace": []})
    trace = result.get("agent_trace", [])
    scores = [int(x.get("confidence", 0)) for x in trace]
    overall = round(sum(scores) / max(1, len(scores)))
    return {
        "summary": result.get("summary", ""), "root_cause": result.get("root_cause", ""), "confidence": result.get("confidence", 0),
        "hypothesis": result.get("hypothesis", ""), "steps": result.get("steps", []), "actions": result.get("actions", []),
        "evidence": result.get("evidence", []), "rag_context": result.get("rag_context", []), "timeline": result.get("timeline", []),
        "risk": result.get("risk", "UNKNOWN"), "agent_trace": trace, "llm_used": result.get("llm_used", False),
        "generated_at": result.get("generated_at", datetime.now(timezone.utc).isoformat()),
        "evaluation": {
            "overall_pipeline_confidence": overall,
            "root_cause_confidence": result.get("confidence", 0),
            "agent_count": len(trace),
            "evidence_count": len(result.get("evidence", [])),
            "rag_documents": len(result.get("rag_context", [])),
            "diagnosis_steps": len(result.get("steps", [])),
            "approval_required": sum(1 for a in result.get("actions", []) if a.get("risk") == "APPROVAL"),
            "blocked_actions": sum(1 for a in result.get("actions", []) if a.get("risk") == "BLOCKED"),
            "llm_enabled": bool(result.get("llm_used", False)),
            "methodology": "Heuristic evidence-weighted confidence; not ground-truth accuracy or a guarantee of correctness."
        }
    }
