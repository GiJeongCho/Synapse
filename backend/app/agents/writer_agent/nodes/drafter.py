"""드래프트 작성 노드(§6)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.writer_agent.prompts import DRAFT_PROMPT
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger

log = logger(__name__)


async def draft_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """아웃라인과 sources를 기반으로 초안을 작성한다."""
    log.info("[writer] draft_node 시작 | iteration=%d", state.get("iteration", 0))

    llm = get_llm_for_agent("writer")
    sources_text = json.dumps(state.get("sources", []), ensure_ascii=False, indent=2)

    chain = DRAFT_PROMPT | llm
    response = await chain.ainvoke(
        {"outline": state.get("outline", ""), "sources": sources_text},
        config=config,
    )

    draft = response.content

    log.info("[writer] draft_node 완료 | length=%d", len(draft))

    return {
        "draft": draft,
        "messages": [{"role": "drafter", "content": draft}],
    }
