# app/agents/wintheam_extractor/graph/nodes/increment_retry_node.py

from typing import Any, Dict

from app.agents.wintheam_extractor.graph.agent_state import WinThemeExtractorState


def increment_retry_node(
    state: WinThemeExtractorState,
) -> Dict[str, Any]:
    """
    Increment the retry counter before regenerating the retrieval blueprint.

    This node does not modify the generated response or validation feedback.
    It only prepares the graph for another generation attempt.
    """

    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "current_step": "increment_retry",
        "status": "processing",
    }