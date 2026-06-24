"""Summarize 노드(§6) — 확장된 컨텍스트를 요약한다."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.graph_agent.prompts import SUMMARIZE_PROMPT
from app.agents.graph_agent.state import GraphAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def summarize_node(
    state: GraphAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    query = state["query"]
    expanded = state.get("expanded_context", "")

    log.info("Summarize 시작: query=%s", query[:60])

    llm = get_llm_for_agent("graph")
    messages = SUMMARIZE_PROMPT.format_messages(
        query=query,
        expanded_context=expanded,
    )
    response = await llm.ainvoke(messages)
    result = extract_json_from_llm_response(response.content)

    summary = result.get("summary", "")
    log.info("Summarize 완료: summary_len=%d", len(summary))

    return {"summary": summary}
