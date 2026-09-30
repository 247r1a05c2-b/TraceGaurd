SAFE_ACTIONS = {
    "Freeze further checkout deployments": "SAFE",
    "Inspect database connection pool and saturation": "SAFE",
    "Compare v2.8.1 with the previous checkout release": "SAFE",
    "Rollback checkout deployment": "APPROVAL",
}


def classify_action(action: str) -> dict[str, str]:
    risk = SAFE_ACTIONS.get(action, "BLOCKED")
    if risk == "SAFE":
        message = "Read-only or reversible diagnostic action."
    elif risk == "APPROVAL":
        message = "Production mutation detected. Human approval is required."
    else:
        message = "Unknown action blocked by default-deny policy."
    return {"action": action, "risk": risk, "message": message}
