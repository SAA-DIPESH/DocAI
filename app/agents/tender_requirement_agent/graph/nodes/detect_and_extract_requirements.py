import time
from typing import Any, Dict

from app.agents.tender_requirement_agent.chains.detector_chain import (
    detect_and_extract,
)
from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementState,
)
from app.agents.tender_requirement_agent.utils.helper import (
    update_latency,
)
from app.infrastructure.token_usage_logger import TokenUsageService


DEFAULT_TOKEN_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "models": {},
}


async def detect_and_extract_requirements_node(
    state: TenderRequirementState,
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    # Ensure token_usage always exists
    token_usage = state.setdefault(
        "token_usage",
        DEFAULT_TOKEN_USAGE.copy(),
    )

    try:

        raw_response, response = await detect_and_extract(
            chunk_text=state["chunk_text"],
        )

        # Update token usage from LLM response
        TokenUsageService.update_state(
            state,
            raw_response,
        )

        requirements = response.get(
            "requirements",
            [],
        )

        return {
            "requirements": requirements,
            "token_usage": state.get("token_usage", token_usage),
            "workflow_status": "processing",
            "current_step": "detect_and_extract_requirements",
            "error": None,
            "node_latencies": update_latency(
                state,
                "detect_and_extract_requirements",
                start_time,
            ),
        }

    except Exception as ex:

        return {
            "requirements": [],
            "token_usage": state.get("token_usage", token_usage),
            "workflow_status": "failed",
            "current_step": "detect_and_extract_requirements",
            "error": str(ex),
            "node_latencies": update_latency(
                state,
                "detect_and_extract_requirements",
                start_time,
            ),
        }