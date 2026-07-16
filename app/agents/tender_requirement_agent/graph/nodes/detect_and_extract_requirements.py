import time
from typing import Any, Dict

from app.agents.tender_requirement_agent.chains.detector_chain import detect_and_extract
from app.agents.tender_requirement_agent.graph.agent_state import TenderRequirementState
from app.agents.tender_requirement_agent.utils.helper import update_latency


async def detect_and_extract_requirements_node(state: TenderRequirementState) -> Dict[str, Any]:

    start_time = time.perf_counter()

    try:

        response = await detect_and_extract(
            chunk_text=state["chunk_text"],
        )

        requirements = response.get(
            "requirements",
            [],
        )

        return {
            "requirements": requirements,
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
            "workflow_status": "failed",
            "current_step": "detect_and_extract_requirements",
            "error": str(ex),
            "node_latencies": update_latency(
                state,
                "detect_and_extract_requirements",
                start_time,
            ),
        }