import time
from typing import Dict, Any

from app.agents.wintheam_generator.graph.agent_state import WinThemeState


def select_current_anchor_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Select the current anchor group based on the current anchor index.
    """

    start = time.perf_counter()

    try:
        anchor_groups = state.get("anchor_groups", [])
        current_index = state.get("current_anchor_index", 0)

        latency = round(time.perf_counter() - start, 3)

        if current_index >= len(anchor_groups):
            return {
                "next_step": "end",
                "current_anchor_group": None,
                "current_evidence": [],
                "current_win_theme": None,
                "retrieval_status": None,
                "status": "success",
                "validation_status": "passed",
                "current_step": "select_current_anchor",
                "error": None,
                "node_latencies": {
                    **state.get("node_latencies", {}),
                    "select_current_anchor": latency,
                },
            }

        return {
            "current_anchor_group": anchor_groups[current_index],
            "current_evidence": [],
            "current_win_theme": None,
            "retrieval_status": None,
            "next_step": "continue",
            "status": "success",
            "validation_status": "passed",
            "current_step": "select_current_anchor",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "select_current_anchor": latency,
            },
        }

    except Exception as e:
        latency = round(time.perf_counter() - start, 3)

        return {
            "current_anchor_group": None,
            "current_evidence": [],
            "current_win_theme": None,
            "retrieval_status": "failed",
            "next_step": "end",
            "status": "failed",
            "validation_status": "failed",
            "warnings": [
                *state.get("warnings", []),
                str(e),
            ],
            "current_step": "select_current_anchor",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "select_current_anchor": latency,
            },
        }