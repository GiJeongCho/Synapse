"""Qdrant vector DB client — milvus_client.py 와 동일한 공개 API를 제공한다.

소비자 코드(``vector_store``, ``pipeline`` 등)가 import 경로만 바꿔서 그대로 쓸 수 있도록,
함수 이름/인자/반환값을 ``milvus_client`` 와 동일하게 맞춘다. 내부 구현만 Qdrant API로 작성한다.

Milvus → Qdrant 주요 차이 처리:
- 포인트 ID는 정수/UUID만 허용 → 문자열 청크 ID를 uuid5로 결정적 변환하고 원본은 payload에 보관.
- Milvus 필터 문자열(`field == "value"` [and ...]) → Qdrant ``Filter`` 객체로 번역.
- 거리 메트릭은 COSINE(높을수록 유사) → 기존 임계값 로직과 호환.
임베딩은 milvus_client 와 동일하게 외부 FastAPI embed 서비스(settings.embed_api_url)에 위임한다.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

from app.config import settings

_client: QdrantClient | None = None

# 문자열 ID → 결정적 UUID 변환용 고정 네임스페이스.
_ID_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_uri)
    return _client


def _collection() -> str:
    return settings.qdrant_collection


def ensure_collection() -> None:
    """컬렉션이 없으면 COSINE 거리로 생성한다. (Qdrant는 별도 load 불필요)"""
    client = get_client()
    if not client.collection_exists(_collection()):
        client.create_collection(
            collection_name=_collection(),
            vectors_config=VectorParams(
                size=settings.embedding_dim,
                distance=Distance.COSINE,
            ),
        )


# ---------------------------------------------------------------------------
# ID / 필터 유틸
# ---------------------------------------------------------------------------

def _to_point_id(chunk_id: str) -> str:
    """문자열 청크 ID를 결정적 UUID(문자열)로 변환한다."""
    return str(uuid.uuid5(_ID_NAMESPACE, chunk_id))


_COND_RE = re.compile(r'^\s*(\w+)\s*==\s*(.+?)\s*$')


def _parse_value(raw: str) -> Any:
    raw = raw.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    # 따옴표 없으면 숫자 시도, 실패하면 원문 문자열.
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return raw


def _build_filter(filter_expr: str | None) -> Filter | None:
    """Milvus 필터 문자열(`field == "value"` 를 ` and ` 로 결합)을 Qdrant Filter로 번역한다."""
    if not filter_expr or not filter_expr.strip():
        return None

    conditions: list[FieldCondition] = []
    # ' and ' / ' && ' 로 분리(대소문자 무시).
    parts = re.split(r'\s+(?:and|&&)\s+', filter_expr.strip(), flags=re.IGNORECASE)
    for part in parts:
        m = _COND_RE.match(part)
        if not m:
            # 지원하지 않는 표현식은 무시(검색 자체는 진행).
            continue
        field, raw_val = m.group(1), m.group(2)
        conditions.append(
            FieldCondition(key=field, match=MatchValue(value=_parse_value(raw_val)))
        )

    return Filter(must=conditions) if conditions else None


# ---------------------------------------------------------------------------
# Embedding helper — 외부 FastAPI 서비스 (milvus_client 와 동일)
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str]) -> list[list[float]]:
    """외부 임베딩 API 호출하여 벡터 반환."""
    resp = httpx.post(
        f"{settings.embed_api_url}/embed",
        json={"texts": texts},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def upsert_chunks(
    chunk_ids: list[str],
    texts: list[str],
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
) -> None:
    """청크와 임베딩·메타데이터를 upsert 한다. 원본 chunk_id 는 payload 에 보관한다."""
    ensure_collection()
    client = get_client()

    points: list[PointStruct] = []
    for cid, text, vec, payload in zip(chunk_ids, texts, vectors, payloads):
        points.append(
            PointStruct(
                id=_to_point_id(cid),
                vector=vec,
                payload={"chunk_id": cid, "text": text, **payload},
            )
        )

    client.upsert(collection_name=_collection(), points=points)


def search(
    query_vector: list[float],
    top_k: int = 10,
    filter_expr: str | None = None,
    output_fields: list[str] | None = None,  # 시그니처 호환용(Qdrant는 payload 전체 반환)
) -> list[dict]:
    """시맨틱 유사도 검색. milvus_client.search 와 동일한 형식의 hit dict 리스트 반환."""
    ensure_collection()
    client = get_client()

    response = client.query_points(
        collection_name=_collection(),
        query=query_vector,
        limit=top_k,
        query_filter=_build_filter(filter_expr),
        with_payload=True,
    )

    hits: list[dict] = []
    for point in response.points:
        payload = point.payload or {}
        entry: dict[str, Any] = {
            "id": payload.get("chunk_id", str(point.id)),
            "score": point.score,
        }
        for k, v in payload.items():
            if k == "chunk_id":
                continue
            entry[k] = v
        hits.append(entry)
    return hits


def delete_chunks(chunk_ids: list[str]) -> None:
    """ID로 청크를 삭제한다."""
    client = get_client()
    client.delete(
        collection_name=_collection(),
        points_selector=PointIdsList(points=[_to_point_id(c) for c in chunk_ids]),
    )


def _scroll_all(scroll_filter: Filter | None, limit: int = 1000) -> list[dict]:
    """조건에 맞는 포인트의 payload 리스트를 페이지네이션으로 모두 수집한다."""
    client = get_client()
    records: list[dict] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=_collection(),
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )
        for p in points:
            payload = dict(p.payload or {})
            payload.setdefault("id", payload.get("chunk_id", str(p.id)))
            records.append(payload)
        if offset is None:
            break
    return records


def get_chunks_by_source(source: str) -> list[dict]:
    """특정 문서(source)에 속한 모든 청크를 조회한다."""
    ensure_collection()
    return _scroll_all(
        Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])
    )


def list_sources() -> list[dict]:
    """컬렉션 내 고유 문서(source) 목록을 반환한다."""
    ensure_collection()
    records = _scroll_all(None)

    seen: dict[str, str] = {}
    for r in records:
        src = r.get("source", "")
        if src and src not in seen:
            seen[src] = r.get("doc_type", "unknown")

    return [{"source": s, "doc_type": dt} for s, dt in seen.items()]


def drop_all_chunks() -> None:
    """컬렉션 전체 삭제 후 재생성."""
    client = get_client()
    if client.collection_exists(_collection()):
        client.delete_collection(_collection())
    ensure_collection()


def delete_chunks_by_source(source: str) -> None:
    """특정 문서(source)에 속한 청크를 필터로 삭제한다."""
    client = get_client()
    client.delete(
        collection_name=_collection(),
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source))]
            )
        ),
    )
