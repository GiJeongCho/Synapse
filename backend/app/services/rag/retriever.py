"""검색 진입 함수(§12.5).

Vector + Graph 통합 검색을 ``hybrid_retrieve`` 로 추상화한다.
현재는 Vector 단독으로 동작하며, Graph 결과는 ``GraphStore`` 구현 후 fusion 한다.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.services.rag.vector_store import vector_store

log = logger(__name__)


async def vector_retrieve(
    query: str,
    top_k: Optional[int] = None,
    filter_expr: Optional[str] = None,
) -> List[dict]:
    """Vector DB 시맨틱 검색."""
    return await vector_store.search(query=query, top_k=top_k, filter_expr=filter_expr)


async def hybrid_retrieve(
    query: str,
    top_k: Optional[int] = None,
    filter_expr: Optional[str] = None,
) -> List[dict]:
    """Vector(+Graph) 하이브리드 검색.

    TODO: GraphStore 구현 후 ``settings.rag_fusion_k`` 기반 RRF fusion 추가.
    """
    return await vector_retrieve(query=query, top_k=top_k, filter_expr=filter_expr)


def hybrid_retrieve_sync(
    query: str,
    top_k: Optional[int] = None,
    filter_expr: Optional[str] = None,
) -> List[dict]:
    """동기 진입점(기존 API 호환용)."""
    _ = settings  # 임계값/한도는 vector_store 내부에서 settings 로 적용
    return asyncio.run(hybrid_retrieve(query=query, top_k=top_k, filter_expr=filter_expr))
