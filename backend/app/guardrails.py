SAFE_PATTERNS = [
    "inspect",
    "check",
    "compare",
    "freeze further",
    "review",
    "view",
    "read-only",
]

APPROVAL_PATTERNS = [
    "rollback",
    "restart",
    "scale",
    "deploy",
    "change configuration",
    "failover",
]

BLOCKED_PATTERNS = [
    "delete",
    "drop database",
    "wipe",
    "disable authentication",
]


def classify_action(action: str) -> dict[str, str]:
    normalized = action.strip().lower()
    if any(pattern in normalized for pattern in BLOCKED_PATTERNS):
        risk = "BLOCKED"
        message = "Destructive or high-risk action blocked by default-deny policy."
    elif any(pattern in normalized for pattern in APPROVAL_PATTERNS):
        risk = "APPROVAL"
        message = "Production mutation detected. Human approval is required."
    elif any(pattern in normalized for pattern in SAFE_PATTERNS):
        risk = "SAFE"
        message = "Read-only or reversible diagnostic action."
    else:
        risk = "BLOCKED"
        message = "Unknown action blocked by default-deny policy."
    return {"action": action, "risk": risk, "message": message}
