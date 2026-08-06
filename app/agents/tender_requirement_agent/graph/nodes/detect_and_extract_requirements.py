import time
from typing import Any, Dict

from app.agents.tender_requirement_agent.chains.detector_chain import (
    detect_and_extract_batch,
)

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementBatchState,
)

from app.agents.tender_requirement_agent.utils.helper import (
    update_latency,
)

from app.infrastructure.token_usage_logger import (
    TokenUsageService,
)

DEFAULT_TOKEN_USAGE = {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "models": {},
}


async def detect_and_extract_batch_node(
    state: TenderRequirementBatchState,
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    token_usage = state.get(
        "token_usage",
        DEFAULT_TOKEN_USAGE.copy(),
    )

    try:

        # --------------------------------------------------
        # Collect chunks that passed rule filter
        # --------------------------------------------------

        chunks_to_process = [
            chunk
            for chunk in state["chunks"]
            if chunk.get("should_process", False)
        ]

        # Nothing to process
        if not chunks_to_process:

            updated_chunks = []

            for chunk in state["chunks"]:

                updated_chunks.append(
                    {
                        **chunk,
                        "detection_result": False,
                        "requirements": [],
                    }
                )

            return {
                "chunks": updated_chunks,
                "token_usage": token_usage,
                "workflow_status": "completed",
                "current_step": "detect_and_extract",
                "error": None,
                "node_latencies": update_latency(
                    state,
                    "detect_and_extract",
                    start_time,
                ),
            }

        # --------------------------------------------------
        # Single LLM Call
        # --------------------------------------------------

        raw_response, response = await detect_and_extract_batch(
            chunks_to_process,
        )

        TokenUsageService.update_state(
            state,
            raw_response,
        )

        # --------------------------------------------------
        # Map Result by ChunkId
        # --------------------------------------------------

        response_lookup = {
            item["chunk_id"]: item
            for item in response.get("chunks", [])
        }

        updated_chunks = []

        for chunk in state["chunks"]:

            if not chunk.get("should_process", False):

                updated_chunks.append(
                    {
                        **chunk,
                        "detection_result": False,
                        "requirements": [],
                    }
                )

                continue

            result = response_lookup.get(
                chunk["chunk_id"],
                {},
            )

            updated_chunks.append(
                {
                    **chunk,
                    "detection_result": result.get(
                        "detection_result",
                        False,
                    ),
                    "requirements": result.get(
                        "requirements",
                        [],
                    ),
                }
            )

        return {
            "chunks": updated_chunks,
            "token_usage": state.get(
                "token_usage",
                token_usage,
            ),
            "workflow_status": "processing",
            "current_step": "detect_and_extract",
            "error": None,
            "node_latencies": update_latency(
                state,
                "detect_and_extract",
                start_time,
            ),
        }

    except Exception as ex:

        return {
            "chunks": state["chunks"],
            "token_usage": state.get(
                "token_usage",
                token_usage,
            ),
            "workflow_status": "failed",
            "current_step": "detect_and_extract",
            "error": str(ex),
            "node_latencies": update_latency(
                state,
                "detect_and_extract",
                start_time,
            ),
        }