from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementState,
)

from app.agents.tender_requirement_agent.services.rule_based_filter import (
    rule_based_filter,
)


def rule_filter_node(
    state: TenderRequirementState,
):
    """
    LangGraph node responsible for filtering chunks before
    sending them to the LLM.

    The business logic is implemented in the service layer.
    """

    return rule_based_filter(state)