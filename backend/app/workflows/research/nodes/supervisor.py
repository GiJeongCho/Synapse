"""Supervisor 노드(§9) — 다음 실행할 에이전트를 결정한다."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger
from app.workflows.research.prompts import SUPERVISOR_PROMPT
from app.workflows.research.state import ResearchState

log = logger(__name__)

VALID_AGENTS = {"search", "crawl", "graph", "analyst", "writer", "FINISH"}


async def supervisor_node(
    state: ResearchState,
    config: RunnableConfig,
) -> dict[str, Any]:
    topic = state.get("topic", "")
    instruction = state.get("instruction", "")
    results = state.get("results", [])
    iteration = state.get("iteration", 0)

    results_summary = (
        ", ".join(r.get("agent", "?") for r in results) if results else "없음"
    )

    log.info("Supervisor 판단 시작: topic=%s, iter=%d", topic[:60], iteration)

    llm = get_llm_for_agent("supervisor")
    messages = SUPERVISOR_PROMPT.format_messages(
        topic=topic,
        instruction=instruction,
        results_summary=results_summary,
        iteration=iteration,
    )
    response = await llm.ainvoke(messages)
    result = extract_json_from_llm_response(response.content)

    next_agent = result.get("next_agent", "FINISH")
    if next_agent not in VALID_AGENTS:
        log.warning("유효하지 않은 에이전트: %s → FINISH", next_agent)
        next_agent = "FINISH"

    if iteration >= settings.max_iteration and next_agent != "FINISH":
        log.info("최대 반복 도달, FINISH 강제")
        next_agent = "FINISH"

    new_instruction = result.get("instruction", instruction)

    log.info("Supervisor 결정: next=%s", next_agent)

    return {
        "next_agent": next_agent,
        "instruction": new_instruction,
        "iteration": iteration + 1,
    }


def route_next(state: ResearchState) -> str:
    """Supervisor 결정에 따라 다음 노드를 라우팅한다."""
    return state.get("next_agent", "FINISH")
