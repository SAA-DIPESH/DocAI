import time
from typing import Dict, Any

from app.agents.wintheam_generator.graph.agent_state import WinThemeState


def _build_placeholder_theme(
    anchor_group: Dict[str, Any],
    status: str,
    warning: str,
) -> Dict[str, Any]:
    """Build a placeholder theme when no valid theme can be generated."""

    return {
        "anchor_id": anchor_group.get("anchor_id"),
        "objective": anchor_group.get("objective"),
        "anchor_query": anchor_group.get("anchor_query"),
        "status": status,
        "theme_name": None,
        "theme_statement": None,
        "buyer_value": None,
        "proof_points": [],
        "supporting_evidence_ids": [],
        "warning": warning,
    }


def collect_win_theme_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Collect the generated win theme (or a placeholder) for the current
    anchor group, then advance to the next anchor group.
    """

    start = time.perf_counter()

    try:
        generated_themes = list(state.get("generated_themes", []))

        current_anchor_group = state.get("current_anchor_group")
        generated_theme = state.get("current_win_theme")
        retrieval_status = state.get("retrieval_status")
        anchor_groups = state.get("anchor_groups", [])

        # Case 1: Theme generated successfully
        if generated_theme is not None:
            generated_themes.append(generated_theme)

        # Case 2: No supporting evidence found
        elif retrieval_status == "no_evidence" and current_anchor_group:
            generated_themes.append(
                _build_placeholder_theme(
                    anchor_group=current_anchor_group,
                    status="insufficient_evidence",
                    warning="No evidence found for this anchor group.",
                )
            )

        # Case 3: Retrieval failed
        elif retrieval_status == "failed" and current_anchor_group:
            generated_themes.append(
                _build_placeholder_theme(
                    anchor_group=current_anchor_group,
                    status="failed",
                    warning=state.get("error")
                    or "Evidence retrieval failed for this anchor group.",
                )
            )

        # Case 4: Unexpected retrieval status
        elif current_anchor_group:
            generated_themes.append(
                _build_placeholder_theme(
                    anchor_group=current_anchor_group,
                    status="failed",
                    warning=f"Unexpected retrieval status: {retrieval_status}",
                )
            )

        next_index = state.get("current_anchor_index", 0) + 1

        latency = round(time.perf_counter() - start, 3)

        return {
            "generated_themes": generated_themes,
            "current_anchor_index": next_index,
            "next_step": (
                "continue"
                if next_index < len(anchor_groups)
                else "end"
            ),

            # Reset loop state
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
                "collect_win_theme": latency,
            },
        }

    except Exception as e:
        latency = round(time.perf_counter() - start, 3)

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
                "collect_win_theme": latency,
            },
        }