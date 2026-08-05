from typing import Literal

from langgraph.graph import END

from app.agents.wintheam_generator.graph.agent_state import WinThemeState


def route_after_extract(
    state: WinThemeState,
) -> Literal["select_current_anchor", END]:
    """
    Route after extracting the retrieval blueprint.
    Stop if extraction failed or no anchor groups were produced.
    """

    if state.get("status") == "failed":
        return END

    if not state.get("anchor_groups"):
        return END

    if state.get("next_step") == "end":
        return END

    return "select_current_anchor"


def route_after_select_anchor(
    state: WinThemeState,
) -> Literal["retrieve_evidence", END]:
    """
    Route after selecting the current anchor group.
    Stop if there are no more anchors to process.
    """

    if state.get("status") == "failed":
        return END

    if state.get("next_step") == "end":
        return END

    if state.get("current_anchor_group") is None:
        return END

    return "retrieve_evidence"


def route_after_retrieve_evidence(
    state: WinThemeState,
) -> Literal["win_theme_generator", "collect_win_theme"]:
    """
    Generate a win theme only when retrieval succeeds.
    Otherwise collect the result and continue.
    """

    return (
        "win_theme_generator"
        if state.get("retrieval_status") == "success"
        else "collect_win_theme"
    )


def route_after_collection(
    state: WinThemeState,
) -> Literal["select_current_anchor", END]:
    """
    Continue processing remaining anchor groups or end the workflow.
    """

    if state.get("status") == "failed":
        return END

    return (
        "select_current_anchor"
        if state.get("next_step") == "continue"
        else END
    )