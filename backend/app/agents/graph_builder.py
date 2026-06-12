"""LangGraph DAG builder — assembles the Supervisor-pattern multi-agent
research pipeline using conditional routing."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    analyst_node,
    graph_node,
    orchestrator_node,
    search_node,
    writer_node,
)
from app.agents.state import ResearchState


def _route_after_orchestrator(state: ResearchState) -> str:
    return state.current_step


def _route_after_analyst(state: ResearchState) -> str:
    if state.current_step == "writer":
        return "writer"
    if state.current_step == "graph":
        return "graph"
    return "search"


def build_research_graph() -> StateGraph:
    """Build and compile the LangGraph research pipeline.

    Flow:
      orchestrator → search|graph
        → analyst → (sufficient?) → writer → END
                   → (insufficient?) → search (loop)
    """
    graph = StateGraph(ResearchState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("search", search_node)
    graph.add_node("graph", graph_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "search": "search",
            "graph": "graph",
            "analyst": "analyst",
            "writer": "writer",
        },
    )

    graph.add_edge("search", "analyst")
    graph.add_edge("graph", "analyst")

    graph.add_conditional_edges(
        "analyst",
        _route_after_analyst,
        {
            "writer": "writer",
            "search": "search",
            "graph": "graph",
        },
    )

    graph.add_edge("writer", END)

    return graph.compile()


async def run_research(query: str, domain_filter: str | None = None) -> ResearchState:
    """Execute the full research pipeline and return final state."""
    app = build_research_graph()
    initial_state = ResearchState(query=query, domain_filter=domain_filter)
    final_state = await app.ainvoke(initial_state)
    return final_state
