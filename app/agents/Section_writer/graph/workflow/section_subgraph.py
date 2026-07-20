from langgraph.graph import StateGraph, START, END

from app.agents.Section_writer.schemas.state import SectionState

from app.agents.Section_writer.graph.node.validate_context import validate_context_node
from app.agents.Section_writer.graph.node.section_writer import section_writer_node
from app.agents.Section_writer.graph.node.compliance_check import compliance_check_node
from app.agents.Section_writer.graph.node.merge_section_node import merge_section_node

from app.agents.Section_writer.graph.workflow.conditional_routing import (
    validation_router,
    compliance_router,
)

section_subgraph_builder = StateGraph(SectionState)

section_subgraph_builder.add_node("validate_context", validate_context_node)
section_subgraph_builder.add_node("section_writer", section_writer_node)
section_subgraph_builder.add_node("compliance_check", compliance_check_node)
section_subgraph_builder.add_node("merge_section", merge_section_node)

section_subgraph_builder.add_edge(START, "validate_context")

section_subgraph_builder.add_conditional_edges(
    "validate_context",
    validation_router,
)

section_subgraph_builder.add_edge("section_writer", "compliance_check")

section_subgraph_builder.add_conditional_edges(
    "compliance_check",
    compliance_router,
)

section_subgraph_builder.add_edge("merge_section", END)

section_subgraph = section_subgraph_builder.compile(name="process_section")
