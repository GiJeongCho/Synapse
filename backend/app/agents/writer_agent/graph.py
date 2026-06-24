"""WriterAgent 그래프(§4).

plan → draft → evaluate → [route: replan→draft or finalize→END].
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.writer_agent.nodes.drafter import draft_node
from app.agents.writer_agent.nodes.evaluator import evaluate_node
from app.agents.writer_agent.nodes.planner import plan_node
from app.agents.writer_agent.nodes.replanner import replan_node
from app.agents.writer_agent.state import WriterAgentState
from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)


def _should_replan(state: WriterAgentState) -> str:
    """평가 결과에 따라 재계획 또는 종료를 결정한다."""
    evaluation = state.get("evaluation", {})
    passed = evaluation.get("passed", False)

    if passed or state.get("iteration", 0) >= settings.max_iteration:
        if not passed:
            log.info("[writer] max_iteration 도달 → 최종본 확정")
        return "finalize"
    return "replan"


def _finalize(state: WriterAgentState) -> dict:
    """최종 텍스트를 확정한다."""
    return {"final_text": state.get("draft", "")}


def create_writer_workflow():
    """작성 에이전트 워크플로우를 생성하고 compiled graph를 반환한다."""
    graph = StateGraph(WriterAgentState)

    graph.add_node("plan", plan_node)
    graph.add_node("draft", draft_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("replan", replan_node)
    graph.add_node("finalize", _finalize)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "draft")
    graph.add_edge("draft", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        _should_replan,
        {"replan": "replan", "finalize": "finalize"},
    )
    graph.add_edge("replan", "draft")
    graph.add_edge("finalize", END)

    return graph.compile()
