"""비평 노드(§6)."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.analyst_agent.prompts import CRITIQUE_PROMPT
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def critique_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """현재 분석을 비판적으로 평가한다."""
    log.info("[analyst] critique_node 시작 | iteration=%d", state.get("iteration", 0))

    llm = get_llm_for_agent("analyst")

    chain = CRITIQUE_PROMPT | llm
    response = await chain.ainvoke(
        {"analysis": state.get("analysis", "")},
        config=config,
    )

    parsed = extract_json_from_llm_response(response.content)
    critique = parsed.get("critique", "")

    log.info(
        "[analyst] critique_node 완료 | needs_refinement=%s weaknesses=%d",
        parsed.get("needs_refinement", False),
        len(parsed.get("weaknesses", [])),
    )

    return {
        "critique": critique,
        "iteration": state.get("iteration", 0) + 1,
        "messages": [{"role": "critic", "content": critique}],
    }
