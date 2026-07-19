from typing import Literal
from app.agents.wintheam_generator.graph.agent_state import WinThemeState
from langgraph.graph import END


def route_after_extract(state: WinThemeState):
    """
    Stops the graph if extractor fails or returns no anchor groups.
    """

    if state.get("status") == "failed":
        return END

    if not state.get("anchor_groups"):
        return END

    if state.get("next_step") == "end":
        return END

    return "select_current_anchor"


def route_after_select_anchor(state: WinThemeState):
    """
    Stops the graph if no current anchor group is available.
    """

    if state.get("status") == "failed":
        return END

    if state.get("next_step") == "end":
        return END

    if not state.get("current_anchor_group"):
        return END

    return "retrieve_evidence"


def route_after_retrieve_evidence(state: WinThemeState):
    """
    Sends the workflow to the LLM only when evidence exists.
    Otherwise, collect an insufficient-evidence result and continue the loop.
    """

    retrieval_status = state.get("retrieval_status")

    if retrieval_status == "success":
        return "win_theme_generator"

    if retrieval_status in ["no_evidence", "failed"]:
        return "collect_win_theme"

    return "collect_win_theme"


def route_after_collection(state: WinThemeState):
    """
    Routes the workflow after collecting the current win theme.
    """

    if state.get("status") == "failed":
        return END

    if state.get("next_step") == "continue":
        return "select_current_anchor"

    return END
