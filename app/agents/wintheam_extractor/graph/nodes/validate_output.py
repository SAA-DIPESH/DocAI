# app/agents/wintheam_extractor/graph/nodes/validate_output.py

import json
import time
from typing import Any, Dict
from app.agents.wintheam_extractor.graph.chains.validator_chain import VALIDATION_CHAIN
from app.agents.wintheam_extractor.graph.agent_state import WinThemeExtractorState


def validate_output_node(state: WinThemeExtractorState) -> Dict[str, Any]:
    """
    Validate the generated retrieval blueprint.
    """

    start_time = time.perf_counter()

    try:
        validation_result = VALIDATION_CHAIN.invoke(
            {
                "retrieval_blueprint": json.dumps(
                    state["retrieval_blueprint"],
                    indent=2,
                    ensure_ascii=False,
                )
            }
        )

        print("=" * 80)
        print("VALIDATION RESULT")
        print(validation_result)
        print("=" * 80)

        latency = time.perf_counter() - start_time

        node_latencies = dict(state.get("node_latencies", {}))
        node_latencies["validate_output"] = latency

        return {
            "validation_status": validation_result.get(
                "validation_status",
                "failed",
            ),
            "validation_feedback": validation_result.get(
                "feedback",
                [],
            ),
            "current_step": "validate_output",
            "node_latencies": node_latencies,
        }
    except Exception as exc:

        latency = time.perf_counter() - start_time

        node_latencies = dict(state.get("node_latencies", {}))
        node_latencies["validate_output"] = latency

        return {
            "validation_status": "failed",
            "validation_feedback": [
                f"Validator exception: {str(exc)}"
            ],
            "current_step": "validate_output",
            "error": str(exc),
            "node_latencies": node_latencies,
        }