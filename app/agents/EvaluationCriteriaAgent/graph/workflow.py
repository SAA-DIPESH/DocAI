"""LangGraph workflow construction only."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.EvaluationCriteriaAgent.graph.agent_state import EvaluationCriteriaAgentState


def build_workflow(
    retrieve_node,
    llm_node,
    validate_node,
    output_node,
):
    graph = StateGraph(EvaluationCriteriaAgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("llm", llm_node)
    graph.add_node("validate", validate_node)
    graph.add_node("output", output_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "llm")
    graph.add_edge("llm", "validate")
    graph.add_edge("validate", "output")
    graph.add_edge("output", END)
    return graph.compile()
