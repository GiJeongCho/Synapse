"""정제 노드(§6)."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.analyst_agent.prompts import REFINE_PROMPT
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def refine_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """비평을 반영하여 분석을 정제한다."""
    log.info("[analyst] refine_node 시작 | iteration=%d", state.get("iteration", 0))

    llm = get_llm_for_agent("analyst")

    chain = REFINE_PROMPT | llm
    response = await chain.ainvoke(
        {
            "analysis": state.get("analysis", ""),
            "critique": state.get("critique", ""),
        },
        config=config,
    )

    parsed = extract_json_from_llm_response(response.content)
    refined = parsed.get("refined_analysis", "")

    log.info(
        "[analyst] refine_node 완료 | improvements=%d",
        len(parsed.get("improvements_made", [])),
    )

    return {
        "refined_analysis": refined,
        "analysis": refined,
        "messages": [{"role": "refiner", "content": refined}],
    }
