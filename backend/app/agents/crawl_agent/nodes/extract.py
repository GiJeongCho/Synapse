"""추출 노드(§6) — LLM을 사용하여 원본 콘텐츠에서 의미 있는 텍스트를 추출한다."""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.crawl_agent.prompts import EXTRACT_PROMPT
from app.agents.crawl_agent.state import CrawlAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger

log = logger(__name__)

_MAX_RAW_CONTENT_CHARS = 50_000


async def extract_node(
    state: CrawlAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """raw_content에서 LLM으로 본문 텍스트를 추출한다."""
    raw_content = state.get("raw_content", "")
    url = state.get("url", "")

    log.info("extract_node 시작: url=%s, raw_length=%d", url, len(raw_content))

    truncated = raw_content[:_MAX_RAW_CONTENT_CHARS]

    llm = get_llm_for_agent("crawl")
    messages = EXTRACT_PROMPT.format_messages(
        url=url,
        raw_content=truncated,
    )
    response = await llm.ainvoke(messages)
    extracted_text = response.content.strip()

    log.info("extract_node 완료: extracted_length=%d", len(extracted_text))

    return {"extracted_text": extracted_text}
