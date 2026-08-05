import time
from typing import Any, Dict

from app.agents.wintheam_generator.graph.agent_state import (
    AnchorGroup,
    WinThemeState,
)


def select_current_anchor_node(
    state: WinThemeState,
) -> Dict[str, Any]:
    """
    Select the current anchor group for processing.
    """

    start = time.perf_counter()

    try:
        anchor_groups: list[AnchorGroup] = state["anchor_groups"]
        current_index = state.get("current_anchor_index", 0)

        if current_index >= len(anchor_groups):
            latency = round(time.perf_counter() - start, 3)

            return {
                "next_step": "end",
                "current_anchor_group": None,
                "current_evidence": [],
                "current_win_theme": None,
                "retrieval_status": None,
                "status": "success",
                "current_step": "select_current_anchor",
                "node_latencies": {
                    **state.get("node_latencies", {}),
                    "select_current_anchor": latency,
                },
            }

        latency = round(time.perf_counter() - start, 3)

        return {
            "current_anchor_group": anchor_groups[current_index],
            "current_evidence": [],
            "current_win_theme": None,
            "retrieval_status": None,
            "next_step": "continue",
            "status": "success",
            "current_step": "select_current_anchor",
            "node_latencies": {
                **state.get("node_latencies", {}),
                "select_current_anchor": latency,
            },
        }

    except Exception as exc:
        latency = round(time.perf_counter() - start, 3)

        return {
            "current_anchor_group": None,
            "current_evidence": [],
            "current_win_theme": None,
            "retrieval_status": "failed",
            "next_step": "end",
            "status": "failed",
            "current_step": "select_current_anchor",
            "error": str(exc),
            "warnings": [
                *state.get("warnings", []),
                str(exc),
            ],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "select_current_anchor": latency,
            },
        }