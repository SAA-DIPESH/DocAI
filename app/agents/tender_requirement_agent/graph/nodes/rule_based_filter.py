from app.agents.tender_requirement_agent.services.rule_based_filter import rule_based_filter

def rule_filter_node(state):
    should_process, reason = rule_based_filter(state["chunk_text"])

    return {
        "should_process": should_process,
        "filter_reason": reason,
    }