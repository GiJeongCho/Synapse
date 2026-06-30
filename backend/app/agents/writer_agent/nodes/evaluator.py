"""평가 노드(§6)."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.writer_agent.prompts import EVALUATE_PROMPT
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def evaluate_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """작성된 초안의 품질을 평가한다."""
    log.info("[writer] evaluate_node 시작 | iteration=%d", state.get("iteration", 0))

    llm = get_llm_for_agent("writer")

    chain = EVALUATE_PROMPT | llm
    response = await chain.ainvoke(
        {"draft": state.get("draft", "")},
        config=config,
    )

    parsed = extract_json_from_llm_response(response.content)

    log.info(
        "[writer] evaluate_node 완료 | passed=%s score=%.2f",
        parsed.get("passed", False),
        parsed.get("score", 0.0),
    )

    return {
        "evaluation": parsed,
        "iteration": state.get("iteration", 0) + 1,
        "messages": [{"role": "evaluator", "content": parsed.get("feedback", "")}],
    }
