from typing import Any

from .evaluation import build_evaluation
from .graph import run_graph


def run_agents(events: list[dict[str, Any]]) -> dict[str, Any]:
    result = run_graph(events)
    result["evaluation"] = build_evaluation(result)
    return result
