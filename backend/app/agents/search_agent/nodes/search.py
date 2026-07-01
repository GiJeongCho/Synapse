"""검색 노드(§6) — 내장 RAG MCP 도구로 하이브리드 검색을 수행한다."""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.search_agent.state import SearchAgentState
from app.core.logging import logger
from app.services.mcp import rag_tool

log = logger(__name__)


async def search_node(
    state: SearchAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """RAG MCP 도구(rag_search)로 질의를 검색하고 raw_results를 반환한다."""
    query = state["query"]
    iteration = state.get("iteration", 0)

    log.info("search_node 시작: query=%r, iteration=%d", query, iteration)

    response = await rag_tool.call("rag_search", {"query": query})

    if response.get("status") == "success":
        results = response.get("result", {}).get("results", [])
    else:
        log.warning("search_node RAG MCP 검색 실패: %s", response.get("error"))
        results = []

    log.info("search_node 완료: %d건 검색됨", len(results))

    return {"raw_results": results}
