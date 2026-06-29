"""AnalystAgent 그래프(§4).

analyze → critique → refine → [route: retry or END].
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.analyst_agent.nodes.analyze import analyze_node
from app.agents.analyst_agent.nodes.critique import critique_node
from app.agents.analyst_agent.nodes.refine import refine_node
from app.agents.analyst_agent.state import AnalystAgentState
from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)


def _should_retry(state: AnalystAgentState) -> str:
    """정제 후 재분석이 필요한지 판단한다."""
    if state.get("iteration", 0) >= settings.max_iteration:
        log.info("[analyst] max_iteration 도달 → 종료")
        return "end"
    return "retry"


def create_analyst_workflow():
    """분석 에이전트 워크플로우를 생성하고 compiled graph를 반환한다."""
    graph = StateGraph(AnalystAgentState)

    graph.add_node("analyze", analyze_node)
    graph.add_node("critique", critique_node)
    graph.add_node("refine", refine_node)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "critique")
    graph.add_edge("critique", "refine")
    graph.add_conditional_edges(
        "refine",
        _should_retry,
        {"retry": "analyze", "end": END},
    )

    return graph.compile()
