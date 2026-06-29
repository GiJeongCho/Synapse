"""재계획 노드(§6)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.writer_agent.prompts import REPLAN_PROMPT
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def replan_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """평가 피드백을 반영하여 아웃라인을 수정한다."""
    log.info("[writer] replan_node 시작 | iteration=%d", state.get("iteration", 0))

    llm = get_llm_for_agent("writer")
    evaluation = state.get("evaluation", {})

    chain = REPLAN_PROMPT | llm
    response = await chain.ainvoke(
        {
            "outline": state.get("outline", ""),
            "feedback": evaluation.get("feedback", ""),
            "suggestions": json.dumps(
                evaluation.get("suggestions", []), ensure_ascii=False,
            ),
        },
        config=config,
    )

    parsed = extract_json_from_llm_response(response.content)
    outline = parsed.get("outline", "")

    log.info(
        "[writer] replan_node 완료 | changes=%d",
        len(parsed.get("changes_made", [])),
    )

    return {
        "outline": outline,
        "messages": [{"role": "replanner", "content": outline}],
    }
