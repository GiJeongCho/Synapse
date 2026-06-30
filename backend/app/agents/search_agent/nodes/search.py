"""검색 노드(§6) — 벡터 스토어에서 시맨틱 검색을 수행한다."""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.search_agent.state import SearchAgentState
from app.core.logging import logger
from app.services.rag.vector_store import vector_store

log = logger(__name__)


async def search_node(
    state: SearchAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """벡터 스토어를 통해 질의를 검색하고 raw_results를 반환한다."""
    query = state["query"]
    iteration = state.get("iteration", 0)

    log.info("search_node 시작: query=%r, iteration=%d", query, iteration)

    results = await vector_store.search(query=query)

    log.info("search_node 완료: %d건 검색됨", len(results))

    return {"raw_results": results}
