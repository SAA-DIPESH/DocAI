from typing import Any, Dict

from app.agents.Section_writer.graph.workflow.section_subgraph import section_subgraph
from app.agents.Section_writer.schemas.state import SectionState


async def process_section_node(
    state: SectionState,
) -> Dict[str, Any]:
    result = await section_subgraph.ainvoke(state)

    return {
        "section_results": result.get("section_results", []),
    }
