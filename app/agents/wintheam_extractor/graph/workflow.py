# app/agents/wintheam_extractor/graph/graph.py

from langgraph.graph import END, StateGraph

from app.agents.wintheam_extractor.graph.agent_state import WinThemeExtractorState

from app.agents.wintheam_extractor.graph.nodes.validate_input import (
    validate_input_node,
)
from app.agents.wintheam_extractor.graph.nodes.generate_retrieval_plan import (
    generate_retrieval_plan_node,
)
from app.agents.wintheam_extractor.graph.nodes.validate_output import (
    validate_output_node,
)
from app.agents.wintheam_extractor.graph.nodes.validate_router import (
    input_validation_router,
    validation_router,
    increment_retry_node,
    validation_failed_node,
)

# ==========================================================
# Graph
# ==========================================================

graph_builder = StateGraph(WinThemeExtractorState)

# ==========================================================
# Nodes
# ==========================================================

graph_builder.add_node(
    "validate_input",
    validate_input_node,
)

graph_builder.add_node(
    "generate_retrieval_plan",
    generate_retrieval_plan_node,
)

graph_builder.add_node(
    "validate_output",
    validate_output_node,
)

graph_builder.add_node(
    "increment_retry",
    increment_retry_node,
)

graph_builder.add_node(
    "validation_failed",
    validation_failed_node,
)

# ==========================================================
# Entry
# ==========================================================

graph_builder.set_entry_point("validate_input")

# ==========================================================
# Input Validation
# ==========================================================

graph_builder.add_conditional_edges(
    "validate_input",
    input_validation_router,
    {
        "generate_retrieval_plan": "generate_retrieval_plan",
        "validation_failed": "validation_failed",
    },
)

# ==========================================================
# Generation Flow
# ==========================================================

graph_builder.add_edge(
    "generate_retrieval_plan",
    "validate_output",
)

graph_builder.add_conditional_edges(
    "validate_output",
    validation_router,
    {
        "increment_retry": "increment_retry",
        "validation_failed": "validation_failed",
        "__end__": END,
    },
)

graph_builder.add_edge(
    "increment_retry",
    "generate_retrieval_plan",
)

graph_builder.add_edge(
    "validation_failed",
    END,
)

# ==========================================================
# Compile
# ==========================================================

wintheam_extractor_graph = graph_builder.compile()