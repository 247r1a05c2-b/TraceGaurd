from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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


def retrieve(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    documents = [f"{item['title']} {item['content']} {' '.join(item['tags'])}" for item in KNOWLEDGE_BASE]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(documents + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = sorted(zip(scores, KNOWLEDGE_BASE), key=lambda pair: pair[0], reverse=True)
    return [{**item, "score": round(float(score), 4), "retrieval_mode": "tfidf_vector"} for score, item in ranked[:top_k]]
