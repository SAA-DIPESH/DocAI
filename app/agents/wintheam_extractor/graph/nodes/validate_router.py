from app.agents.wintheam_extractor.graph.agent_state import WintheamState

def validation_router(state: WintheamState):

    if state["validation_status"] == "passed":
        return "__end__"

    if state["retry_count"] >= state["max_retries"]:
        return "__end__"

    return "increment_retry"




def validation_failed_node(state: WintheamState):

    return {
        "status": "failed",
        "current_step": "validation_failed",
        "error": "Maximum retry limit reached.",
    }




def increment_retry_node(state: WintheamState):

    return {
        "retry_count": state["retry_count"] + 1,
        "current_step": "increment_retry",
    }