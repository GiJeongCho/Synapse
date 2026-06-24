"""정리 노드(§6) — LLM을 사용하여 검색 결과를 주제별로 그룹화한다."""
from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.search_agent.prompts import ORGANIZE_PROMPT
from app.agents.search_agent.state import SearchAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def organize_node(
    state: SearchAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """필터링된 결과를 LLM으로 주제별 그룹화한다."""
    filtered = state.get("filtered_results", [])
    query = state["query"]

    log.info("organize_node 시작: %d건 결과 정리", len(filtered))

    llm = get_llm_for_agent("search")
    messages = ORGANIZE_PROMPT.format_messages(
        query=query,
        results=json.dumps(filtered, ensure_ascii=False, indent=2),
    )
    response = await llm.ainvoke(messages)
    organized = extract_json_from_llm_response(response.content)

    log.info("organize_node 완료: %d개 그룹 생성", len(organized))

    return {"organized": organized}
