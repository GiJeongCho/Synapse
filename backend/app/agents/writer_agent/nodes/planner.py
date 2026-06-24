"""계획 노드(§6)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.writer_agent.prompts import PLAN_PROMPT
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def plan_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """topic과 sources를 기반으로 리포트 아웃라인을 생성한다."""
    log.info("[writer] plan_node 시작 | job_id=%s", state.get("job_id"))

    llm = get_llm_for_agent("writer")
    sources_text = json.dumps(state.get("sources", []), ensure_ascii=False, indent=2)

    chain = PLAN_PROMPT | llm
    response = await chain.ainvoke(
        {"topic": state.get("topic", ""), "sources": sources_text},
        config=config,
    )

    parsed = extract_json_from_llm_response(response.content)
    outline = parsed.get("outline", "")

    log.info(
        "[writer] plan_node 완료 | sections=%d",
        len(parsed.get("sections", [])),
    )

    return {
        "outline": outline,
        "iteration": state.get("iteration", 0),
        "messages": [{"role": "planner", "content": outline}],
    }
