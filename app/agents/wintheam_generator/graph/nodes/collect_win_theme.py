import time
from typing import Any, Dict

from app.agents.wintheam_generator.graph.agent_state import (
    AnchorGroup,
    WinTheme,
    WinThemeState,
)


def _build_placeholder_theme(
    anchor_group: AnchorGroup,
    status: str,
    warning: str,
) -> WinTheme:
    """
    Build a placeholder win theme when generation cannot
    produce a valid theme.
    """

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


def collect_win_theme_node(
    state: WinThemeState,
) -> Dict[str, Any]:
    """
    Collect the generated win theme (or placeholder)
    and advance to the next anchor group.
    """

    start = time.perf_counter()

    try:

        generated_themes = list(
            state.get("generated_themes", [])
        )

        current_anchor_group = state.get(
            "current_anchor_group"
        )

        generated_theme = state.get(
            "current_win_theme"
        )

        retrieval_status = state.get(
            "retrieval_status"
        )

        anchor_groups = state.get(
            "anchor_groups",
            [],
        )

        if generated_theme is not None:

            generated_themes.append(
                generated_theme
            )

        elif (
            retrieval_status == "no_evidence"
            and current_anchor_group
        ):

            generated_themes.append(
                _build_placeholder_theme(
                    current_anchor_group,
                    "insufficient_evidence",
                    "No evidence found for this anchor group.",
                )
            )

        elif (
            retrieval_status == "failed"
            and current_anchor_group
        ):

            generated_themes.append(
                _build_placeholder_theme(
                    current_anchor_group,
                    "failed",
                    state.get("error")
                    or "Evidence retrieval failed.",
                )
            )

        elif current_anchor_group:

            generated_themes.append(
                _build_placeholder_theme(
                    current_anchor_group,
                    "failed",
                    f"Unexpected retrieval status: {retrieval_status}",
                )
            )

        next_index = (
            state.get(
                "current_anchor_index",
                0,
            )
            + 1
        )

        latency = round(
            time.perf_counter() - start,
            3,
        )

        return {
            "generated_themes": generated_themes,
            "current_anchor_index": next_index,
            "next_step": (
                "continue"
                if next_index < len(anchor_groups)
                else "end"
            ),
            "current_anchor_group": None,
            "current_evidence": [],
            "current_win_theme": None,
            "retrieval_status": None,
            "retrieved_chunks_count": 0,
            "reranked_chunks_count": 0,
            "status": "success",
            "warnings": state.get(
                "warnings",
                [],
            ),
            "unsupported_claims_removed": state.get(
                "unsupported_claims_removed",
                [],
            ),
            "current_step": "collect_win_theme",
            "error": None,
            "node_latencies": {
                **state.get(
                    "node_latencies",
                    {},
                ),
                "collect_win_theme": latency,
            },
        }

    except Exception as exc:

        latency = round(
            time.perf_counter() - start,
            3,
        )

        return {
            "status": "failed",
            "current_step": "collect_win_theme",
            "error": str(exc),
            "warnings": [
                *state.get(
                    "warnings",
                    [],
                ),
                str(exc),
            ],
            "node_latencies": {
                **state.get(
                    "node_latencies",
                    {},
                ),
                "collect_win_theme": latency,
            },
        }