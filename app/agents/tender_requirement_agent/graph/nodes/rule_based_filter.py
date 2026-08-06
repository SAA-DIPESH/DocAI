from typing import Any, Dict

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementBatchState,
)

from app.agents.tender_requirement_agent.services.rule_based_filter import (
    rule_based_filter,
)


def rule_filter_batch_node(
    state: TenderRequirementBatchState,
) -> Dict[str, Any]:
    """
    Apply rule-based filtering to every chunk in the batch.

    Each chunk is evaluated independently using the
    rule_based_filter() service.
    """

    updated_chunks = []

    for chunk in state["chunks"]:

        filter_result = rule_based_filter(chunk)

        updated_chunks.append(
            {
                **chunk,
                **filter_result,
            }
        )

    return {
        **state,
        "chunks": updated_chunks,
        "workflow_status": "processing",
        "current_step": "rule_filter",
        "error": None,
    }