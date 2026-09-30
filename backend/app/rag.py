from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KNOWLEDGE_BASE = [
    {"id": "RB-001", "title": "Checkout 5xx runbook", "content": "Check recent deployments, error-rate spikes, application logs, request traces, and dependency health before considering rollback.", "tags": ["checkout", "500", "deployment", "rollback"]},
    {"id": "RB-002", "title": "Database pool runbook", "content": "Inspect connection-pool saturation, connection acquisition latency, timeout rate, database health, and recent schema or configuration changes.", "tags": ["database", "timeout", "pool", "saturation"]},
    {"id": "RB-003", "title": "Safe rollback policy", "content": "Rollback is a production mutation. Prepare the rollback plan, verify the previous known-good release, and require human approval before execution.", "tags": ["rollback", "approval", "production", "guardrail"]},
    {"id": "RB-004", "title": "Incident communication", "content": "Maintain a chronological incident timeline and communicate observed evidence, hypothesis, confidence, and next diagnostic action.", "tags": ["timeline", "incident", "evidence", "communication"]},
    {"id": "RB-005", "title": "Deployment regression runbook", "content": "Compare the changed version with the previous release, inspect changed configuration and database dependencies, and validate with a canary when possible.", "tags": ["deployment", "regression", "release", "canary"]},
]


def retrieve(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    documents = [f"{item['title']} {item['content']} {' '.join(item['tags'])}" for item in KNOWLEDGE_BASE]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(documents + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = sorted(zip(scores, KNOWLEDGE_BASE), key=lambda pair: pair[0], reverse=True)
    return [{**item, "score": round(float(score), 4)} for score, item in ranked[:top_k]]
