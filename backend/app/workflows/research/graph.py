"""Research Supervisor 그래프(§9) — Supervisor → Worker → Supervisor 루프."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.workflows.research.nodes.supervisor import route_next, supervisor_node
from app.workflows.research.nodes.workers import (
    analyst_worker,
    crawl_worker,
    graph_worker,
    search_worker,
    writer_worker,
)
from app.workflows.research.state import ResearchState


def create_research_workflow():
    """리서치 Supervisor 워크플로우를 컴파일한다."""
    workflow = StateGraph(ResearchState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("search", search_worker)
    workflow.add_node("crawl", crawl_worker)
    workflow.add_node("graph", graph_worker)
    workflow.add_node("analyst", analyst_worker)
    workflow.add_node("writer", writer_worker)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "search": "search",
            "crawl": "crawl",
            "graph": "graph",
            "analyst": "analyst",
            "writer": "writer",
            "FINISH": END,
        },
    )

    for worker in ("search", "crawl", "graph", "analyst", "writer"):
        workflow.add_edge(worker, "supervisor")

    return workflow.compile()
