"""Vector DB 추상화(§12).

노드/도구는 Milvus 클라이언트를 직접 호출하지 않고 ``VectorStore`` 를 통해서만 접근한다.
Top-K/임계값은 하드코딩 금지 → ``settings.*``.
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.core.config import settings
from app.core.errors.exceptions import VectorDBConnectionError
from app.core.logging import logger
from app.vectordb import milvus_client

log = logger(__name__)


class VectorStore:
    """Qdrant/Milvus 시맨틱 검색 래퍼."""

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[str] = None,
    ) -> List[dict]:
        """질의 텍스트를 임베딩해 유사 청크를 반환한다.

        Args:
            query: 검색 질의.
            top_k: 결과 수(미지정 시 ``settings.vector_search_top_k``).
            filter_expr: Milvus 필터식(doc_type/importance 등).
        Returns:
            score 포함 hit dict 리스트.
        """
        k = top_k or settings.vector_search_top_k
        try:
            vector = milvus_client.embed_texts([query])[0]
            hits = milvus_client.search(query_vector=vector, top_k=k, filter_expr=filter_expr)
        except Exception as exc:  # noqa: BLE001
            log.error("[VectorStore] 검색 실패: %s", exc, exc_info=True)
            raise VectorDBConnectionError(details={"cause": str(exc)})

        threshold = settings.vector_search_similarity_threshold
        return [h for h in hits if h.get("score", 0) >= threshold]

    async def upsert(
        self,
        chunk_ids: List[str],
        texts: List[str],
        payloads: List[dict[str, Any]],
    ) -> None:
        vectors = milvus_client.embed_texts(texts)
        milvus_client.upsert_chunks(chunk_ids, texts, vectors, payloads)


vector_store = VectorStore()
