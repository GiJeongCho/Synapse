"""SearchAgent 그래프(§4).

search → filter → organize → evaluate → [retry: search / done: END]
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.search_agent.nodes.evaluate import evaluate_node
from app.agents.search_agent.nodes.filter import filter_node
from app.agents.search_agent.nodes.organize import organize_node
from app.agents.search_agent.nodes.search import search_node
from app.agents.search_agent.state import SearchAgentState
from app.core.config import settings


def _route_after_evaluate(state: SearchAgentState) -> str:
    """평가 결과와 반복 횟수에 따라 재검색 또는 종료를 라우팅한다."""
    evaluation = state.get("evaluation", {})

    if evaluation.get("sufficient"):
        return "done"

    iteration = state.get("iteration", 0)
    if iteration >= settings.max_iteration:
        return "done"

    return "retry"


def create_search_workflow():
    """검색 에이전트 워크플로우를 컴파일하여 반환한다."""
    workflow = StateGraph(SearchAgentState)

    workflow.add_node("search", search_node)
    workflow.add_node("filter", filter_node)
    workflow.add_node("organize", organize_node)
    workflow.add_node("evaluate", evaluate_node)

    workflow.set_entry_point("search")
    workflow.add_edge("search", "filter")
    workflow.add_edge("filter", "organize")
    workflow.add_edge("organize", "evaluate")
    workflow.add_conditional_edges("evaluate", _route_after_evaluate, {
        "done": END,
        "retry": "search",
    })

    return workflow.compile()
