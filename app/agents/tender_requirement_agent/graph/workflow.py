from langgraph.graph import START, END, StateGraph

from app.agents.tender_requirement_agent.graph.agent_state import (
    TenderRequirementBatchState,
)

from app.agents.tender_requirement_agent.graph.nodes.rule_based_filter import (
    rule_filter_batch_node,
)

from app.agents.tender_requirement_agent.graph.nodes.detect_and_extract_requirements import (
    detect_and_extract_batch_node,
)

from app.agents.tender_requirement_agent.graph.nodes.process_requirements_batch import (
    process_requirements_batch_node,
)

from app.agents.tender_requirement_agent.graph.nodes.save_chunk_status_batch import (
    save_chunk_status_batch_node,
)


# ==========================================================
# Build Graph
# ==========================================================

def build_tender_requirement_graph():

    workflow = StateGraph(TenderRequirementBatchState)

    # ------------------------------------------------------
    # Nodes
    # ------------------------------------------------------

    workflow.add_node(
        "rule_filter",
        rule_filter_batch_node,
    )

    workflow.add_node(
        "detect_and_extract",
        detect_and_extract_batch_node,
    )

    workflow.add_node(
        "process_requirements",
        process_requirements_batch_node,
    )

    workflow.add_node(
        "save_chunk_status",
        save_chunk_status_batch_node,
    )

    # ------------------------------------------------------
    # Flow
    # ------------------------------------------------------

    workflow.add_edge(
        START,
        "rule_filter",
    )

    workflow.add_edge(
        "rule_filter",
        "detect_and_extract",
    )

    workflow.add_edge(
        "detect_and_extract",
        "process_requirements",
    )

    workflow.add_edge(
        "process_requirements",
        "save_chunk_status",
    )

    workflow.add_edge(
        "save_chunk_status",
        END,
    )

    return workflow.compile()


# ==========================================================
# Graph Instance
# ==========================================================

tender_requirement_graph = build_tender_requirement_graph()