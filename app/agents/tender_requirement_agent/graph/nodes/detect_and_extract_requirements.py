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

async def detect_and_extract_requirements_node(
    state: TenderRequirementState,
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    try:

        raw_response, response = await detect_and_extract(
            chunk_text=state["chunk_text"],
        )

        # Track token usage
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
            "token_usage": state["token_usage"],
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
            "token_usage": state["token_usage"],
            "workflow_status": "failed",
            "current_step": "detect_and_extract_requirements",
            "error": str(ex),
            "node_latencies": update_latency(
                state,
                "detect_and_extract_requirements",
                start_time,
            ),
        }