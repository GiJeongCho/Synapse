"""정규화 노드(§6) — 추출된 텍스트를 LLM으로 정리한다."""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.crawl_agent.prompts import NORMALIZE_PROMPT
from app.agents.crawl_agent.state import CrawlAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger

log = logger(__name__)


async def normalize_node(
    state: CrawlAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """extracted_text를 LLM으로 정규화한다."""
    extracted_text = state.get("extracted_text", "")

    log.info("normalize_node 시작: text_length=%d", len(extracted_text))

    llm = get_llm_for_agent("crawl")
    messages = NORMALIZE_PROMPT.format_messages(extracted_text=extracted_text)
    response = await llm.ainvoke(messages)
    normalized_text = response.content.strip()

    log.info("normalize_node 완료: normalized_length=%d", len(normalized_text))

    return {"normalized_text": normalized_text}
