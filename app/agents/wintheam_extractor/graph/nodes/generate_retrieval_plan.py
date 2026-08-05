# app/agents/wintheam_extractor/graph/nodes/generate_retrieval_plan.py

import json
import time
from typing import Any, Dict

from app.agents.wintheam_extractor.graph.chains.extract_chain import (
    RETRIEVAL_PLAN_CHAIN,
)
from app.agents.wintheam_extractor.graph.agent_state import WinThemeExtractorState


def generate_retrieval_plan_node(state: WinThemeExtractorState) -> Dict[str, Any]:
    """
    Generate an evidence retrieval blueprint using the LLM.
    """

    start_time = time.perf_counter()

    try:
        response = RETRIEVAL_PLAN_CHAIN.invoke(
            {
                "company_id": state["company_id"],
                "industry": state["industry"],
                "cpv_codes": json.dumps(
                    state["cpv_codes"],
                    indent=2,
                ),
                "validation_feedback": "\n".join(
                    state.get("validation_errors", [])
                ),
            }
        )

        latency = time.perf_counter() - start_time

        node_latencies = dict(state.get("node_latencies", {}))
        node_latencies["generate_retrieval_plan"] = latency

        return {
            "retrieval_blueprint": response,
            "raw_llm_response": json.dumps(
                response,
                indent=2,
                ensure_ascii=False,
            ),
            "status": "processing",
            "current_step": "generate_retrieval_plan",
            "error": None,
            "node_latencies": node_latencies,
        }

    except Exception as exc:

        latency = time.perf_counter() - start_time

        node_latencies = dict(state.get("node_latencies", {}))
        node_latencies["generate_retrieval_plan"] = latency

        return {
            "status": "failed",
            "current_step": "generate_retrieval_plan",
            "error": str(exc),
            "node_latencies": node_latencies,
        }