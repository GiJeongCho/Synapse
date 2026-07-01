"""RAG 검색 내장(builtin) MCP 도구.

벡터·BM25·그래프 하이브리드 검색을 에이전트가 MCP 인터페이스로 호출하게 한다.

RAG 검색은 Milvus·Neo4j·임베딩 서비스(앱 내부)에 접근해야 하므로, 격리된
subprocess 도구(tool_runtime)가 아니라 앱 프로세스 내부에서 직접 실행되는
내장 도구로 제공한다. 반환 형태는 ``execute_tool`` 과 동일한 ``{status, result}`` 로
맞추어 에이전트/파이프라인이 일반 MCP 도구처럼 다룰 수 있게 한다.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.services.rag import graph_store, hybrid_retrieve, rerank, vector_store

log = logger(__name__)

# tool_runtime / 레지스트리가 인식하는 도구 식별자.
TOOL_ID = "builtin-rag-search"
FUNCTIONS = ["rag_search", "vector_search", "graph_search"]


def _build_filter(doc_type: str | None, importance: str | None) -> str | None:
    """Milvus 필터식을 구성한다 (search API와 동일 규칙)."""
    parts: list[str] = []
    if doc_type:
        parts.append(f'doc_type == "{doc_type}"')
    if importance:
        parts.append(f'importance == "{importance}"')
    return " and ".join(parts) if parts else None


async def rag_search(
    query: str,
    top_k: int | None = None,
    doc_type_filter: str | None = None,
    importance_filter: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """하이브리드 검색(벡터+BM25+그래프) 후 리랭킹하여 상위 청크를 반환한다."""
    k = top_k or settings.vector_search_top_k
    filter_expr = _build_filter(doc_type_filter, importance_filter)

    candidates = await hybrid_retrieve(query=query, top_k=k * 3, filter_expr=filter_expr)
    results = rerank(query=query, candidates=candidates, top_k=k)

    log.info("[RAG MCP] rag_search: query=%r → %d건", query[:60], len(results))
    return {"query": query, "count": len(results), "results": results}


async def vector_search(
    query: str,
    top_k: int | None = None,
    doc_type_filter: str | None = None,
    importance_filter: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """벡터(시맨틱) 검색만 수행한다."""
    filter_expr = _build_filter(doc_type_filter, importance_filter)
    results = await vector_store.search(query=query, top_k=top_k, filter_expr=filter_expr)

    log.info("[RAG MCP] vector_search: query=%r → %d건", query[:60], len(results))
    return {"query": query, "count": len(results), "results": results}


async def graph_search(
    query: str,
    limit: int | None = None,
    **_: Any,
) -> dict[str, Any]:
    """그래프(Neo4j) 검색만 수행한다 — 조문 번호 직접 조회 / Article fulltext."""
    results = await graph_store.search(query=query, limit=limit)

    log.info("[RAG MCP] graph_search: query=%r → %d건", query[:60], len(results))
    return {"query": query, "count": len(results), "results": results}


_DISPATCH = {
    "rag_search": rag_search,
    "vector_search": vector_search,
    "graph_search": graph_search,
}


async def call(
    function_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """내장 RAG 도구 함수를 실행하고 execute_tool과 동일한 형태로 반환한다."""
    func = _DISPATCH.get(function_name)
    if func is None:
        return {
            "status": "error",
            "error": f"알 수 없는 RAG 함수: {function_name}",
            "available": list(_DISPATCH),
        }

    try:
        result = await func(**(arguments or {}))
        return {"status": "success", "result": result}
    except Exception as exc:  # noqa: BLE001
        log.error("[RAG MCP] 실행 실패: %s — %s", function_name, exc, exc_info=True)
        return {"status": "error", "error": str(exc), "function": function_name}
