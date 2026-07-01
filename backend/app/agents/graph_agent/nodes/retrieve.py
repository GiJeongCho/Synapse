"""Retrieve 노드(§6) — 내장 RAG MCP 도구로 그래프 컨텍스트를 가져온다.

Neo4j 그래프 검색(조문 번호/Article fulltext)으로 관련 노드를 찾아
``context`` 에 채운다. 그래프 결과가 비면 하이브리드 검색으로 폴백한다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.graph_agent.state import GraphAgentState
from app.core.logging import logger
from app.services.mcp import rag_tool

log = logger(__name__)


async def retrieve_node(
    state: GraphAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """그래프 검색으로 context를 채운다 (없으면 하이브리드 검색 폴백)."""
    query = state["query"]

    log.info("retrieve_node 시작: query=%s", query[:60])

    response = await rag_tool.call("graph_search", {"query": query})
    context: list[dict[str, Any]] = []
    if response.get("status") == "success":
        context = response.get("result", {}).get("results", [])

    # 그래프 결과가 비면 하이브리드 검색으로 폴백한다.
    if not context:
        fallback = await rag_tool.call("rag_search", {"query": query})
        if fallback.get("status") == "success":
            context = fallback.get("result", {}).get("results", [])
        log.info("retrieve_node 그래프 결과 없음 → 하이브리드 폴백: %d건", len(context))
    else:
        log.info("retrieve_node 완료: 그래프 %d건", len(context))

    return {"context": context}
