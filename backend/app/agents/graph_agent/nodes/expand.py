"""Expand 노드(§6) — 관련 개념을 확장한다."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.graph_agent.prompts import EXPAND_PROMPT
from app.agents.graph_agent.state import GraphAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def expand_node(
    state: GraphAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    query = state["query"]
    context = state.get("context", [])

    log.info("Expand 시작: query=%s, context_count=%d", query[:60], len(context))

    llm = get_llm_for_agent("graph")
    messages = EXPAND_PROMPT.format_messages(
        query=query,
        context=json.dumps(context, ensure_ascii=False, indent=2),
    )
    response = await llm.ainvoke(messages)
    result = extract_json_from_llm_response(response.content)

    expanded = result.get("expanded_context", "")
    log.info("Expand 완료: entities=%d", len(result.get("entities", [])))

    return {"expanded_context": expanded}
