import time
from typing import Dict, Any
from app.agents.wintheam_generator.graph.agent_state import WinThemeState


def select_current_anchor_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Selects the current anchor group for the loop using current_anchor_index.
    """

    start = time.perf_counter()

    try:
        anchor_groups = state.get("anchor_groups", [])
        current_index = state.get("current_anchor_index", 0)

        if current_index >= len(anchor_groups):
            end = time.perf_counter()

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
                    "select_current_anchor": round(end - start, 3),
                },
            }

        current_anchor_group = anchor_groups[current_index]

        end = time.perf_counter()

        return {
            "current_anchor_group": current_anchor_group,
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
                "select_current_anchor": round(end - start, 3),
            },
        }

    except Exception as e:
        end = time.perf_counter()

        return {
            "current_anchor_group": None,
            "current_evidence": [],
            "current_win_theme": None,
            "retrieval_status": "failed",
            "next_step": "end",
            "status": "failed",
            "validation_status": "failed",
            "warnings": [*state.get("warnings", []), str(e)],
            "current_step": "select_current_anchor",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "select_current_anchor": round(end - start, 3),
            },
        }
