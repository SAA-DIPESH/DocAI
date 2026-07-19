import time
from typing import Dict, Any

from app.agents.wintheam_generator.graph.agent_state import WinThemeState
from app.agents.wintheam_generator.services.qdrant_service import CompanyRetriever


def retrieve_evidence_node(state: WinThemeState) -> Dict[str, Any]:
    """
    Retrieves Qdrant evidence for the current anchor group only.
    Sets retrieval_status so the graph can route safely:
    - success: evidence found
    - no_evidence: retrieval worked, but no chunks found
    - failed: retrieval raised an exception
    """

    start = time.perf_counter()

    try:
        company_id = state["company_id"]
        current_anchor_group = state.get("current_anchor_group")

        if not current_anchor_group:
            end = time.perf_counter()
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
                    "retrieve_evidence": round(end - start, 3),
                },
            }

        retriever = CompanyRetriever()

        retrieval_result = retriever.retrieve(
            company_id=company_id,
            anchor_group=current_anchor_group,
            top_k=5,
            search_limit=10,
        )

        current_evidence = retrieval_result.get("evidence", [])

        if current_evidence:
            retrieval_status = "success"
            status = "success"
            validation_status = "passed"
        else:
            retrieval_status = "no_evidence"
            status = "insufficient_evidence"
            validation_status = "failed"

        end = time.perf_counter()

        return {
            "current_evidence": current_evidence,
            "retrieval_status": retrieval_status,
            "status": status,
            "validation_status": validation_status,
            "current_step": "retrieve_evidence",
            "error": None,
            "node_latencies": {
                **state.get("node_latencies", {}),
                "retrieve_evidence": round(end - start, 3),
            },
        }

    except Exception as e:
        end = time.perf_counter()

        return {
            "current_evidence": [],
            "retrieval_status": "failed",
            "status": "failed",
            "validation_status": "failed",
            "warnings": [*state.get("warnings", []), str(e)],
            "current_step": "retrieve_evidence",
            "error": str(e),
            "node_latencies": {
                **state.get("node_latencies", {}),
                "retrieve_evidence": round(end - start, 3),
            },
        }
