from langgraph.graph import (START,END,StateGraph)
from app.agents.tender_requirement_agent.graph.agent_state import TenderRequirementState
from app.agents.tender_requirement_agent.graph.nodes.detect_and_extract_requirements import detect_and_extract_requirements_node
from app.agents.tender_requirement_agent.graph.nodes.process_all_requirements import process_requirements_node
from app.agents.tender_requirement_agent.graph.nodes.save_chunk_status import save_chunk_status_node
from app.agents.tender_requirement_agent.graph.nodes.rule_based_filter import rule_filter_node


# routing function
def route_after_filter(state: TenderRequirementState):
    if state["should_process"]:
        return "detect_and_extract_requirements"

    return "save_chunk_status"



def build_tender_requirement_graph():

    workflow = StateGraph(TenderRequirementState)

    workflow.add_node("rule_filter", rule_filter_node)
    workflow.add_node("detect_and_extract_requirements",detect_and_extract_requirements_node)
    workflow.add_node("process_requirements",process_requirements_node)
    workflow.add_node("save_chunk_status",save_chunk_status_node)

    
    workflow.add_edge(START, "rule_filter")

    workflow.add_conditional_edges(
        "rule_filter",
        route_after_filter,
        {
            "detect_and_extract_requirements": "detect_and_extract_requirements",
            "save_chunk_status": "save_chunk_status",
        },
    )
    workflow.add_edge("detect_and_extract_requirements","process_requirements")
    workflow.add_edge("process_requirements","save_chunk_status")
    workflow.add_edge("save_chunk_status",END,)

    return workflow.compile()


tender_requirement_graph = build_tender_requirement_graph()