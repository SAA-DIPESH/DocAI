from langgraph.graph import StateGraph, START, END
from app.agents.Section_writer.schemas.state import ProposalGenerationState,SectionState
from app.agents.Section_writer.graph.node.context_generator import context_builder_node
# from app.agents.Section_writer.graph.node.process_section import merge_section_node
from app.agents.Section_writer.graph.workflow.conditional_routing import route_sections
from langgraph.graph import StateGraph, START, END

from app.agents.Section_writer.schemas.state import ProposalGenerationState

from app.agents.Section_writer.graph.node.context_generator import (
    context_builder_node,
)

from app.agents.Section_writer.graph.node.validate_context import (
    validate_context_node,
)

from app.agents.Section_writer.graph.node.section_writer import (
    section_writer_node,
)

from app.agents.Section_writer.graph.node.compliance_check import (
    compliance_check_node,
)

from app.agents.Section_writer.graph.node.merge_section_node import (
    merge_section_node,
)

from app.agents.Section_writer.graph.workflow.conditional_routing import (
    route_sections,
    validation_router,
    compliance_router,
)

# workflow = StateGraph(ProposalGenerationState)

# workflow = StateGraph(ProposalGenerationState)


# workflow.add_node(
#     "context_builder",
#     context_builder_node
# )

# workflow.add_node(
#     "process_section",
#     process_section_node
# )

# workflow.add_edge(
#     START,
#     "context_builder"
# )

# workflow.add_conditional_edges(
#     "context_builder",
#     route_sections
# )

# workflow.add_edge(
#     "process_section",
#     END
# )


# graph = workflow.compile()


# workflow.add_node(
#     "context_builder",
#     context_builder_node,
# )

# workflow.add_node(
#     "validate_context",
#     validate_context_node,
# )

# workflow.add_node(
#     "section_writer",
#     section_writer_node,
# )

# workflow.add_node(
#     "compliance_check",
#     compliance_check_node,
# )

# workflow.add_node(
#     "merge_section",
#     merge_section_node,
# )


# workflow.add_edge(
#     START,
#     "context_builder",
# )


# workflow.add_conditional_edges(
#     "context_builder",
#     route_sections,
# )


# workflow.add_conditional_edges(
#     "validate_context",
#     validation_router,
# )


# workflow.add_edge(
#     "section_writer",
#     "compliance_check",
# )


# workflow.add_conditional_edges(
#     "compliance_check",
#     compliance_router,
# )


# workflow.add_edge(
#     "merge_section",
#     END,
# )


# graph = workflow.compile()



from app.agents.Section_writer.graph.node.process_section import process_section_node

workflow = StateGraph(ProposalGenerationState)

workflow.add_node("context_builder", context_builder_node)
workflow.add_node("process_section", process_section_node)

workflow.add_edge(START, "context_builder")

workflow.add_conditional_edges("context_builder", route_sections)

workflow.add_edge("process_section", END)

graph = workflow.compile()
