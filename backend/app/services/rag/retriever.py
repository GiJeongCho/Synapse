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
from app.services.rag.bm25_store import bm25_store

log = logger(__name__)


async def vector_retrieve(
    query: str,
    top_k: Optional[int] = None,
    filter_expr: Optional[str] = None,
) -> List[dict]:
    """Vector DB 시맨틱 검색."""
    return await vector_store.search(query=query, top_k=top_k, filter_expr=filter_expr)


def hybrid_retrieve_sync(
    query: str,
    top_k: Optional[int] = None,
    filter_expr: Optional[str] = None,
) -> List[dict]:
    """동기 진입점(기존 API 호환용)."""
    return asyncio.run(hybrid_retrieve(query=query, top_k=top_k, filter_expr=filter_expr))

def _rrf_score(rank: int, k: int = 60) -> float:
    """Reciprocal Rank Fusion 점수 계산."""
    return 1.0 / (k + rank)
async def hybrid_retrieve(
    query: str,
    top_k: int | None = None,
    filter_expr: str | None = None,
) -> list[dict]:
    k = top_k or settings.vector_search_top_k

    # 1. 벡터 검색
    vector_hits = await vector_retrieve(query=query, top_k=k * 3, filter_expr=filter_expr)

    # 2. BM25 검색
    bm25_hits = bm25_store.search(query=query, top_k=k * 3)

    # 3. 벡터 결과에 RRF 점수 부여
    vector_scores: dict[str, float] = {}
    for rank, hit in enumerate(vector_hits):
        vector_scores[hit["id"]] = _rrf_score(rank)

    # 4. BM25 결과에 RRF 점수 부여
    bm25_scores: dict[str, float] = {}
    for rank, hit in enumerate(bm25_hits):
        bm25_scores[hit["id"]] = _rrf_score(rank)

    # 5. 합산
    all_ids = set(vector_scores) | set(bm25_scores)
    merged: list[dict] = []
    vector_map = {h["id"]: h for h in vector_hits}
    for cid in all_ids:
        rrf = vector_scores.get(cid, 0) + bm25_scores.get(cid, 0)
        hit = vector_map.get(cid, {"id": cid})
        hit["rrf_score"] = round(rrf, 6)
        merged.append(hit)
    merged.sort(key=lambda x: x["rrf_score"], reverse=True)
    return merged[:k]