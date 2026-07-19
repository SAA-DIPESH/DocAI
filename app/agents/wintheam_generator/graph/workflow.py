from langgraph.graph import StateGraph, END

from app.agents.wintheam_generator.graph.agent_state import WinThemeState
from app.agents.wintheam_generator.graph.nodes.wintheam_extract import extract_win_theme_node
from app.agents.wintheam_generator.graph.nodes.select_current_anchor import select_current_anchor_node
from app.agents.wintheam_generator.graph.nodes.retrieve_chunk import retrieve_evidence_node
from app.agents.wintheam_generator.graph.nodes.wintheam_generator import win_theme_generator_node
from app.agents.wintheam_generator.graph.nodes.collect_win_theme import collect_win_theme_node
from app.agents.wintheam_generator.graph.nodes.routes_nodes import route_after_extract, route_after_collection, route_after_retrieve_evidence, route_after_select_anchor


def route_after_collection(state: WinThemeState):
    if state.get("next_step") == "continue":
        return "select_current_anchor"

    return END


graph_builder = StateGraph(WinThemeState)

graph_builder.add_node("extract_win_theme", extract_win_theme_node)
graph_builder.add_node("select_current_anchor", select_current_anchor_node)
graph_builder.add_node("retrieve_evidence", retrieve_evidence_node)
graph_builder.add_node("win_theme_generator", win_theme_generator_node)
graph_builder.add_node("collect_win_theme", collect_win_theme_node)

graph_builder.set_entry_point("extract_win_theme")

graph_builder.add_conditional_edges(
    "extract_win_theme",
    route_after_extract,
    {
        "select_current_anchor": "select_current_anchor",
        END: END,
    },
)

graph_builder.add_conditional_edges(
    "select_current_anchor",
    route_after_select_anchor,
    {
        "retrieve_evidence": "retrieve_evidence",
        END: END,
    },
)

graph_builder.add_conditional_edges(
    "retrieve_evidence",
    route_after_retrieve_evidence,
    {
        "win_theme_generator": "win_theme_generator",
        "collect_win_theme": "collect_win_theme",
    },
)

graph_builder.add_edge("win_theme_generator", "collect_win_theme")

graph_builder.add_conditional_edges(
    "collect_win_theme",
    route_after_collection,
    {
        "select_current_anchor": "select_current_anchor",
        END: END,
    },
)

win_theme_graph = graph_builder.compile()



# ---------- Save Mermaid Diagram ----------
# output_dir = Path("diagrams")
# output_dir.mkdir(exist_ok=True)

# png_bytes = win_theme_graph.get_graph().draw_mermaid_png()

# output_file = output_dir / "wintheam_generator_workflow.png"

# with open(output_file, "wb") as f:
#     f.write(png_bytes)

# print(f"Workflow diagram saved to: {output_file}")

