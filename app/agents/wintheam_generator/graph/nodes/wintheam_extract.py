import time
from typing import Any, Dict
from app.agents.wintheam_extractor.graph.workflow import wintheam_extractor_graph
from app.agents.wintheam_generator.graph.agent_state import WinThemeState


DEFAULT_RULES = {
    "minimum_evidence_items": 2,
    "minimum_distinct_documents": 2,
}


def extract_win_theme_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Generate the retrieval blueprint by invoking the Win Theme Extractor graph.
    """

    start = time.perf_counter()

    extractor_state = {
        "request_id": state["request_id"],
        "company_id": state["company_id"],
        "industry": state["industry"],
        "cpv_codes": state["cpv_codes"],

        "retrieval_blueprint": None,
        "raw_llm_response": None,

        "validation_status": None,
        "validation_feedback": [],

        "retry_count": 0,
        "max_retries": 2,

        "status": "pending",
        "current_step": None,
        "error": None,

        "node_latencies": {},
    }

    try:

        extractor_result = wintheam_extractor_graph.invoke(
            extractor_state
        )

        print("=" * 80)
        print("EXTRACTOR RESULT")
        print(extractor_result)
        print("=" * 80)

        extractor_response = extractor_result.get(
            "retrieval_blueprint"
        )

        if extractor_response is None:
            return {
                "context": {},
                "anchor_groups": [],
                "current_anchor_index": 0,
                "generated_themes": [],
                "next_step": "end",
                "status": "failed",
                "validation_status": "failed",
                "current_step": "extract_win_theme",
                "error": "Extractor returned retrieval_blueprint=None",
                "warnings": [
                    "Extractor returned retrieval_blueprint=None"
                ],
                "node_latencies": {
                    **state.get("node_latencies", {}),
                    "extract_win_theme": round(
                        time.perf_counter() - start,
                        3,
                    ),
                },
            }

        raw_anchor_groups = extractor_response.get(
            "anchor_groups",
            [],
        )

        anchor_groups = [
            {
                "anchor_id": group.get(
                    "anchor_id",
                    f"ANCHOR_{index + 1:03d}",
                ),
                "objective": group.get("objective"),
                "anchor_query": group.get("anchor_query"),
                "anchor_tags": group.get(
                    "anchor_tags",
                    [],
                ),
                "query_variants": group.get(
                    "query_variants",
                    [],
                ),
                "preferred_document_types": group.get(
                    "preferred_document_types",
                    [],
                ),
                "metadata_should_match": group.get(
                    "metadata_should_match",
                    {},
                ),
                "extract_for_win_theme": group.get(
                    "extract_for_win_theme",
                    [],
                ),
                "search_priority": group.get(
                    "search_priority",
                    index + 1,
                ),
            }
            for index, group in enumerate(raw_anchor_groups)
        ]

        procurement_context = extractor_response.get(
            "procurement_context",
            {},
        )

        context = {
            "company_id": state["company_id"],
            "cpv_codes": state["cpv_codes"],
            "procurement_context": procurement_context,
        }

        latency = round(
            time.perf_counter() - start,
            3,
        )

        return {
            "context": context,
            "anchor_groups": anchor_groups,
            "current_anchor_index": 0,
            "generated_themes": [],
            "rules": state.get(
                "rules",
                DEFAULT_RULES,
            ),
            "next_step": (
                "continue"
                if anchor_groups
                else "end"
            ),
            "status": (
                "success"
                if anchor_groups
                else "insufficient_evidence"
            ),
            "validation_status": extractor_result.get(
                "validation_status",
                "passed",
            ),
            "current_step": "extract_win_theme",
            "error": extractor_result.get("error"),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "extract_win_theme": latency,
            },
        }

    except Exception as exc:

        latency = round(
            time.perf_counter() - start,
            3,
        )

        return {
            "context": {},
            "anchor_groups": [],
            "current_anchor_index": 0,
            "generated_themes": [],
            "next_step": "end",
            "status": "failed",
            "validation_status": "failed",
            "current_step": "extract_win_theme",
            "error": str(exc),
            "warnings": [
                *state.get("warnings", []),
                str(exc),
            ],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "extract_win_theme": latency,
            },
        }