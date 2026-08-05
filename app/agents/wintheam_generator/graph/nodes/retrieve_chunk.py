import time
from typing import Any, Dict

from app.agents.wintheam_generator.graph.agent_state import (
    AnchorGroup,
    WinThemeState,
)
from app.agents.wintheam_generator.services.qdrant_service import (
    COMPANY_RETRIEVER,
)


def retrieve_evidence_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Retrieve supporting evidence for the current anchor group.
    """

    start = time.perf_counter()

    try:
        company_id = state["company_id"]
        current_anchor_group: AnchorGroup | None = state.get(
            "current_anchor_group"
        )

        if current_anchor_group is None:
            latency = round(time.perf_counter() - start, 3)

            return {
                "current_evidence": [],
                "retrieval_status": "failed",
                "retrieved_chunks_count": 0,
                "reranked_chunks_count": 0,
                "status": "failed",
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

        print("=" * 80)
        print(retrieval_result)
        print("=" * 80)

        current_evidence = retrieval_result.get(
            "evidence",
            [],
        )

        latency = round(time.perf_counter() - start, 3)

        return {
            "current_evidence": current_evidence,
            "retrieval_status": (
                "success"
                if current_evidence
                else "no_evidence"
            ),
            "retrieved_chunks_count": retrieval_result.get(
                "retrieved_count",
                len(current_evidence),
            ),
            "reranked_chunks_count": retrieval_result.get(
                "reranked_count",
                len(current_evidence),
            ),
            "status": "success",
            "current_step": "retrieve_evidence",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "retrieve_evidence": latency,
            },
        }

    except Exception as exc:
        latency = round(time.perf_counter() - start, 3)

        return {
            "current_evidence": [],
            "retrieval_status": "failed",
            "retrieved_chunks_count": 0,
            "reranked_chunks_count": 0,
            "status": "failed",
            "current_step": "retrieve_evidence",
            "error": str(exc),
            "warnings": [
                *state.get("warnings", []),
                str(exc),
            ],
            "node_latencies": {
                **state.get("node_latencies", {}),
                "retrieve_evidence": latency,
            },
        }