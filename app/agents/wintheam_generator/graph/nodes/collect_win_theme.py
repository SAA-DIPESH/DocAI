import time
from typing import Dict, Any
from app.agents.wintheam_generator.graph.agent_state import WinThemeState


def collect_win_theme_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Collects the current win theme or records insufficient evidence,
    then moves the loop to the next anchor group.
    """

    start = time.perf_counter()

    try:
        generated_themes = list(state.get("generated_themes", []))

        current_anchor_group = state.get("current_anchor_group")
        current_win_theme = state.get("current_win_theme")
        retrieval_status = state.get("retrieval_status")

        # Case 1: Theme generated successfully
        if current_win_theme:
            generated_themes.append(current_win_theme)

        # Case 2: No evidence found for this anchor
        elif retrieval_status == "no_evidence" and current_anchor_group:
            generated_themes.append({
                "anchor_id": current_anchor_group.get("anchor_id"),
                "objective": current_anchor_group.get("objective"),
                "anchor_query": current_anchor_group.get("anchor_query"),
                "status": "insufficient_evidence",
                "theme_name": None,
                "theme_statement": None,
                "buyer_value": None,
                "proof_points": [],
                "supporting_evidence_ids": [],
                "warning": "No evidence found for this anchor group.",
            })

        # Case 3: Retrieval failed for this anchor
        elif retrieval_status == "failed" and current_anchor_group:
            generated_themes.append({
                "anchor_id": current_anchor_group.get("anchor_id"),
                "objective": current_anchor_group.get("objective"),
                "anchor_query": current_anchor_group.get("anchor_query"),
                "status": "failed",
                "theme_name": None,
                "theme_statement": None,
                "buyer_value": None,
                "proof_points": [],
                "supporting_evidence_ids": [],
                "warning": state.get("error") or "Evidence retrieval failed for this anchor group.",
            })

        next_index = state.get("current_anchor_index", 0) + 1

        next_step = (
            "continue"
            if next_index < len(state.get("anchor_groups", []))
            else "end"
        )

        end = time.perf_counter()

        return {
            "generated_themes": generated_themes,
            "current_anchor_index": next_index,
            "next_step": next_step,

            # Reset current loop fields
            "current_anchor_group": None,
            "current_evidence": [],
            "current_win_theme": None,
            "retrieval_status": None,

            "status": "success",
            "validation_status": "passed",
            "current_step": "collect_win_theme",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "collect_win_theme": round(end - start, 3),
            },
        }

    except Exception as e:
        end = time.perf_counter()

        return {
            "status": "failed",
            "validation_status": "failed",
            "warnings": [
                *state.get("warnings", []),
                str(e),
            ],
            "current_step": "collect_win_theme",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "collect_win_theme": round(end - start, 3),
            },
        }
