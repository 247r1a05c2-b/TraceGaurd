from typing import Any

from .graph import run_graph


def analyze_incident(events: list[dict[str, Any]]) -> dict[str, Any]:
    return run_graph(events)
