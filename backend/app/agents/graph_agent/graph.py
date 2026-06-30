"""GraphAgent 그래프(§4) — retrieve → expand → summarize (선형)."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.graph_agent.nodes.expand import expand_node
from app.agents.graph_agent.nodes.retrieve import retrieve_node
from app.agents.graph_agent.nodes.summarize import summarize_node
from app.agents.graph_agent.state import GraphAgentState


def create_graph_workflow():
    """그래프 에이전트 워크플로우를 컴파일한다."""
    workflow = StateGraph(GraphAgentState)

    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("expand", expand_node)
    workflow.add_node("summarize", summarize_node)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "expand")
    workflow.add_edge("expand", "summarize")
    workflow.add_edge("summarize", END)

    return workflow.compile()
