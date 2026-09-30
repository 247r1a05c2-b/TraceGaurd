from typing import Any

KNOWLEDGE_BASE = [
    {"title": "Checkout 5xx runbook", "content": "Check recent deployments, error-rate spikes, application logs, and dependency health before considering rollback."},
    {"title": "Database pool runbook", "content": "Inspect pool saturation, connection timeouts, database health, and recent schema or configuration changes."},
    {"title": "Safe rollback policy", "content": "Rollback is a production mutation. Prepare the rollback plan and require human approval before execution."},
    {"title": "Incident communication", "content": "Maintain an incident timeline and communicate observed evidence, hypothesis, confidence, and next action."},
]


def retrieve(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    terms = {word.lower() for word in query.split() if len(word) > 3}
    scored = []
    for item in KNOWLEDGE_BASE:
        text = f"{item['title']} {item['content']}".lower()
        score = sum(1 for term in terms if term in text)
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item | {"score": score} for score, item in scored[:top_k]]
