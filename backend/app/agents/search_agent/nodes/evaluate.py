"""평가 노드(§6) — 검색 결과가 질의에 충분한지 LLM으로 판단한다."""
from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.search_agent.prompts import EVALUATE_PROMPT
from app.agents.search_agent.state import SearchAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def evaluate_node(
    state: SearchAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """검색 결과 충분성을 평가하고 iteration을 증가시킨다."""
    organized = state.get("organized", [])
    query = state["query"]
    iteration = state.get("iteration", 0)

    log.info("evaluate_node 시작: iteration=%d", iteration)

    llm = get_llm_for_agent("search")
    messages = EVALUATE_PROMPT.format_messages(
        query=query,
        results=json.dumps(organized, ensure_ascii=False, indent=2),
    )
    response = await llm.ainvoke(messages)
    evaluation = extract_json_from_llm_response(response.content)

    new_iteration = iteration + 1

    log.info(
        "evaluate_node 완료: sufficient=%s, iteration=%d",
        evaluation.get("sufficient"),
        new_iteration,
    )

    return {"evaluation": evaluation, "iteration": new_iteration}
