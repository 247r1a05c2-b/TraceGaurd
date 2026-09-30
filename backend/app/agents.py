from typing import Any

from .graph import run_graph


def run_agents(events: list[dict[str, Any]]) -> dict[str, Any]:
    return run_graph(events)
