"""Meta-Agent 파이프라인 그래프(§4).

requirements → tool_retriever → provisioner → evaluator
                                      ↑              │
                                      └── retry ──────┘ (max 3)
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.meta_agent.nodes.evaluator import evaluator
from app.agents.meta_agent.nodes.provisioner import provisioner
from app.agents.meta_agent.nodes.requirements import requirements_analyzer
from app.agents.meta_agent.nodes.tool_retriever import tool_retriever
from app.agents.meta_agent.state import MetaAgentState
from app.core.config import settings


def _route_after_eval(state: MetaAgentState) -> str:
    """Evaluator 결과에 따라 재시도/완료를 라우팅한다."""
    test_result = state.get("test_result", {})

    if test_result.get("passed"):
        return "done"

    if test_result.get("_max_retries_exceeded"):
        return "done"

    retry_count = state.get("retry_count", 0)
    if retry_count >= settings.meta_max_pipeline_retries:
        return "done"

    return "retry"


def create_meta_agent_workflow():
    """에이전트 생성 파이프라인 워크플로우를 컴파일한다."""
    workflow = StateGraph(MetaAgentState)

    workflow.add_node("requirements", requirements_analyzer)
    workflow.add_node("tool_retriever", tool_retriever)
    workflow.add_node("provisioner", provisioner)
    workflow.add_node("evaluator", evaluator)

    workflow.set_entry_point("requirements")
    workflow.add_edge("requirements", "tool_retriever")
    workflow.add_edge("tool_retriever", "provisioner")
    workflow.add_edge("provisioner", "evaluator")
    workflow.add_conditional_edges("evaluator", _route_after_eval, {
        "done": END,
        "retry": "provisioner",
    })

    return workflow.compile()
