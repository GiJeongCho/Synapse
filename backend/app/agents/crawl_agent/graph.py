"""CrawlAgent 그래프(§4).

fetch → extract → normalize (선형 파이프라인).
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.crawl_agent.nodes.extract import extract_node
from app.agents.crawl_agent.nodes.fetch import fetch_node
from app.agents.crawl_agent.nodes.normalize import normalize_node
from app.agents.crawl_agent.state import CrawlAgentState


def create_crawl_workflow():
    """크롤 에이전트 워크플로우를 컴파일하여 반환한다."""
    workflow = StateGraph(CrawlAgentState)

    workflow.add_node("fetch", fetch_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("normalize", normalize_node)

    workflow.set_entry_point("fetch")
    workflow.add_edge("fetch", "extract")
    workflow.add_edge("extract", "normalize")
    workflow.add_edge("normalize", END)

    return workflow.compile()
