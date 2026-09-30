import math
import re
from typing import Any

RUNBOOKS = [
    {"id": "RB-001", "type": "runbook", "title": "Checkout 5xx runbook", "content": "Check recent deployments, error-rate spikes, application logs, request traces, and dependency health before considering rollback.", "tags": ["checkout", "500", "deployment", "rollback"]},
    {"id": "RB-002", "type": "runbook", "title": "Database pool runbook", "content": "Inspect connection-pool saturation, connection acquisition latency, timeout rate, database health, and recent schema or configuration changes.", "tags": ["database", "timeout", "pool", "saturation"]},
    {"id": "RB-003", "type": "runbook", "title": "Safe rollback policy", "content": "Rollback is a production mutation. Prepare the rollback plan, verify the previous known-good release, and require human approval before execution.", "tags": ["rollback", "approval", "production", "guardrail"]},
    {"id": "RB-004", "type": "runbook", "title": "Incident communication", "content": "Maintain a chronological incident timeline and communicate observed evidence, hypothesis, confidence, and next diagnostic action.", "tags": ["timeline", "incident", "evidence", "communication"]},
    {"id": "RB-005", "type": "runbook", "title": "Deployment regression runbook", "content": "Compare the changed version with the previous release, inspect changed configuration and database dependencies, and validate with a canary when possible.", "tags": ["deployment", "regression", "release", "canary"]},
]

HISTORICAL_INCIDENTS = [
    {"id": "INC-H001", "type": "historical", "title": "Checkout pool saturation after release", "content": "A checkout release increased database connection usage and produced HTTP 500s followed by connection acquisition timeouts. Verification focused on pool saturation and comparison with the previous release.", "tags": ["checkout", "database", "500", "timeout", "release"]},
    {"id": "INC-H002", "type": "historical", "title": "Payments timeout dependency incident", "content": "A downstream payment dependency slowed request completion. The diagnostic path correlated latency spikes with dependency health before any rollback decision.", "tags": ["payments", "timeout", "dependency", "latency"]},
    {"id": "INC-H003", "type": "historical", "title": "Order service deployment regression", "content": "A deployment introduced an application regression. The team compared the current and known-good versions, validated the hypothesis with telemetry, and used a human-approved rollback.", "tags": ["orders", "deployment", "regression", "rollback"]},
]

KNOWLEDGE_BASE = RUNBOOKS + HISTORICAL_INCIDENTS


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _tfidf_scores(query: str, documents: list[str]) -> list[float]:
    query_tokens = _tokens(query)
    doc_tokens = [_tokens(doc) for doc in documents]
    document_count = len(doc_tokens)
    document_frequency: dict[str, int] = {}
    for tokens in doc_tokens:
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    def vector(tokens: list[str]) -> dict[str, float]:
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        total = max(1, len(tokens))
        result = {}
        for token, count in counts.items():
            idf = math.log((1 + document_count) / (1 + document_frequency.get(token, 0))) + 1
            result[token] = (count / total) * idf
        return result

    query_vector = vector(query_tokens)
    query_norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1.0
    scores = []
    for tokens in doc_tokens:
        doc_vector = vector(tokens)
        dot = sum(query_vector.get(token, 0.0) * value for token, value in doc_vector.items())
        doc_norm = math.sqrt(sum(value * value for value in doc_vector.values())) or 1.0
        scores.append(dot / (query_norm * doc_norm))
    return scores


def retrieve(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    documents = [f"{item['title']} {item['content']} {' '.join(item['tags'])}" for item in KNOWLEDGE_BASE]
    scores = _tfidf_scores(query, documents)
    ranked = sorted(zip(scores, KNOWLEDGE_BASE), key=lambda pair: pair[0], reverse=True)
    return [{**item, "score": round(float(score), 4), "retrieval_mode": "tfidf_vector"} for score, item in ranked[:top_k]]
