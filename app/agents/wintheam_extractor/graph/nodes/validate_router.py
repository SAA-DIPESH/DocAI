# app/agents/wintheam_extractor/graph/nodes/validate_router.py

from typing import Any, Dict

from app.agents.wintheam_extractor.graph.agent_state import WinThemeExtractorState


# ==========================================================
# Input Validation Router
# ==========================================================

def input_validation_router(state: WinThemeExtractorState) -> str:
    """
    Route after input validation.
    """

    if state["status"] == "invalid_input":
        return "validation_failed"

    return "generate_retrieval_plan"


# ==========================================================
# Output Validation Router
# ==========================================================

def validation_router(state: WinThemeExtractorState) -> str:
    """
    Decide whether to:
    - finish
    - retry
    - fail
    """

    validation_status = state.get("validation_status", "failed")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if validation_status == "passed":
        return "__end__"

    if retry_count < max_retries:
        return "increment_retry"

    return "validation_failed"


# ==========================================================
# Retry Node
# ==========================================================

def increment_retry_node(
    state: WinThemeExtractorState,
) -> Dict[str, Any]:
    """
    Increment retry count before regenerating the blueprint.
    """

    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "current_step": "increment_retry",
        "status": "processing",
    }


# ==========================================================
# Failure Node
# ==========================================================

def validation_failed_node(
    state: WinThemeExtractorState,
) -> Dict[str, Any]:
    """
    Final failure state.
    """

    return {
        "status": "failed",
        "current_step": "validation_failed",
    }