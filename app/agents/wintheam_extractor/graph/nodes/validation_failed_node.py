# app/agents/wintheam_extractor/graph/nodes/validate_router.py

from typing import Any, Dict

from app.agents.wintheam_extractor.graph.agent_state import WinThemeExtractorState


def validation_failed_node(
    state: WinThemeExtractorState,
) -> Dict[str, Any]:
    """
    Final failure node.

    Executed when:
    - Input validation fails
    - Output validation fails after all retries
    """

    validation_feedback = state.get("validation_feedback", [])

    error_message = (
        "Win Theme retrieval blueprint generation failed."
    )

    if validation_feedback:
        error_message += " Validation failed after maximum retries."

    return {
        "status": "failed",
        "current_step": "validation_failed",
        "error": error_message,
    }