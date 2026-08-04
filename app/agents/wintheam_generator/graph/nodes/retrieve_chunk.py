import time
from typing import Any, Dict

from app.agents.wintheam_generator.graph.agent_state import WinThemeState
from app.agents.wintheam_generator.services.qdrant_service import (
    COMPANY_RETRIEVER,
)


def retrieve_evidence_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Retrieve supporting evidence from Qdrant for the current anchor group.

    Retrieval statuses:
    - success: Evidence found.
    - no_evidence: Retrieval succeeded but no evidence matched.
    - failed: Retrieval could not be completed.
    """

    start = time.perf_counter()

    try:
        company_id = state["company_id"]
        current_anchor_group = state.get("current_anchor_group")

        if current_anchor_group is None:
            latency = round(time.perf_counter() - start, 3)

            return {
                "current_evidence": [],
                "retrieval_status": "failed",
                "status": "failed",
                "validation_status": "failed",
                "current_step": "retrieve_evidence",
                "error": "No current anchor group selected.",
                "warnings": [
                    *state.get("warnings", []),
                    "No current anchor group selected.",
                ],
                "node_latencies": {
                    **state.get("node_latencies", {}),
                    "retrieve_evidence": latency,
                },
            }

        retrieval_result = COMPANY_RETRIEVER.retrieve(
            company_id=company_id,
            anchor_group=current_anchor_group,
            top_k=5,
            search_limit=10,
        )

        current_evidence = retrieval_result.get("evidence", [])

        latency = round(time.perf_counter() - start, 3)

        return {
            "current_evidence": current_evidence,
            "retrieval_status": (
                "success" if current_evidence else "no_evidence"
            ),
            "status": (
                "success"
                if current_evidence
                else "insufficient_evidence"
            ),
            "validation_status": (
                "passed"
                if current_evidence
                else "failed"
            ),
            "current_step": "retrieve_evidence",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "retrieve_evidence": latency,
            },
        }

    except Exception as e:
        latency = round(time.perf_counter() - start, 3)

        return {
            "current_evidence": [],
            "retrieval_status": "failed",
            "status": "failed",
            "validation_status": "failed",
            "warnings": [
                *state.get("warnings", []),
                str(e),
            ],
            "current_step": "retrieve_evidence",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "retrieve_evidence": latency,
            },
        }