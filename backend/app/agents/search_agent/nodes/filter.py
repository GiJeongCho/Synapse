"""필터 노드(§6) — 유사도 임계값 기반으로 검색 결과를 필터링한다."""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.search_agent.state import SearchAgentState
from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)


async def filter_node(
    state: SearchAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """raw_results에서 유사도 임계값 이상인 항목만 남긴다."""
    raw_results = state.get("raw_results", [])
    threshold = settings.vector_search_similarity_threshold

    log.info("filter_node 시작: %d건, threshold=%.2f", len(raw_results), threshold)

    filtered = [
        r for r in raw_results
        if r.get("score", 0) >= threshold
    ]

    log.info("filter_node 완료: %d → %d건 필터링", len(raw_results), len(filtered))

    return {"filtered_results": filtered}
