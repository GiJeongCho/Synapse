"""분석 노드(§6)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.analyst_agent.prompts import ANALYZE_PROMPT
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def analyze_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """주어진 topic과 sources를 기반으로 구조화된 분석을 생성한다."""
    log.info("[analyst] analyze_node 시작 | job_id=%s", state.get("job_id"))

    llm = get_llm_for_agent("analyst")
    sources_text = json.dumps(state.get("sources", []), ensure_ascii=False, indent=2)

    chain = ANALYZE_PROMPT | llm
    response = await chain.ainvoke(
        {"topic": state.get("topic", ""), "sources": sources_text},
        config=config,
    )

    parsed = extract_json_from_llm_response(response.content)
    analysis = parsed.get("analysis", "")

    log.info(
        "[analyst] analyze_node 완료 | findings=%d confidence=%.2f",
        len(parsed.get("key_findings", [])),
        parsed.get("confidence", 0.0),
    )

    return {
        "analysis": analysis,
        "iteration": state.get("iteration", 0),
        "messages": [{"role": "analyst", "content": analysis}],
    }
