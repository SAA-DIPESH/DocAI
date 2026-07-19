# app/graph/graph.py

from langgraph.graph import StateGraph, END
from app.agents.wintheam_extractor.graph.agent_state import WintheamState
from app.agents.wintheam_extractor.graph.nodes.generate_retrieval_plan import generate_retrieval_plan_node
from app.agents.wintheam_extractor.graph.nodes.validate_output import validate_output_node
from app.agents.wintheam_extractor.graph.nodes.validate_router import increment_retry_node, validation_failed_node, validation_router


graph_builder = StateGraph(WintheamState)

# ==========================================================
# Nodes
# ==========================================================
graph_builder.add_node("generate_retrieval_plan",generate_retrieval_plan_node)
graph_builder.add_node("validate_output",validate_output_node)
graph_builder.add_node("increment_retry",increment_retry_node)
graph_builder.add_node("validation_failed",validation_failed_node)

# ==========================================================
# Entry Point
# ==========================================================
graph_builder.set_entry_point("generate_retrieval_plan")

# ==========================================================
# Main Flow
# ==========================================================
graph_builder.add_edge("generate_retrieval_plan","validate_output")
graph_builder.add_conditional_edges(
    "validate_output",
    validation_router,
    {
        "increment_retry": "increment_retry",
        "validation_failed": "validation_failed",
        "__end__": END,
    },
)

graph_builder.add_edge("increment_retry","generate_retrieval_plan")
graph_builder.add_edge("validation_failed",END)

# ==========================================================
# Compile
# ==========================================================
wintheam_extractor_graph = graph_builder.compile()

# ---------- Save Mermaid Diagram ----------
# output_dir = Path("diagrams")
# output_dir.mkdir(exist_ok=True)

# png_bytes = wintheam_extractor_graph.get_graph().draw_mermaid_png()

# with open(output_dir / "wintheam_extractor_workflow.png", "wb") as f:
#     f.write(png_bytes)

# print(f"Workflow diagram saved to: {output_dir / 'wintheam_extractor_workflow.png'}")