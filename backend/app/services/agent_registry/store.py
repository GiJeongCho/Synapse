"""Agent Registry — Qdrant 기반 CRUD.

생성된 에이전트를 저장하고 요구사항 유사도로 기존 에이전트를 검색한다.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

from app.core.config import settings
from app.core.logging import logger
from app.vectordb.qdrant_client import _to_point_id, embed_texts, get_client

log = logger(__name__)


def _collection() -> str:
    return settings.meta_registry_collection


def ensure_collection() -> None:
    client = get_client()
    if not client.collection_exists(_collection()):
        client.create_collection(
            collection_name=_collection(),
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )
        log.info("Agent Registry 컬렉션 생성: %s", _collection())


def _parse_json_fields(record: dict[str, Any]) -> dict[str, Any]:
    for field in ("agent_spec", "mcp_tools", "project_files", "test_result", "graph_structure"):
        val = record.get(field)
        if isinstance(val, str):
            try:
                record[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
    return record


def register(record: dict[str, Any]) -> None:
    """에이전트 레코드를 Registry에 저장한다."""
    ensure_collection()
    client = get_client()

    embedding = record.get("request_embedding")
    if not embedding:
        embedding = embed_texts([record["user_request"]])[0]

    payload = {
        "agent_id": record["agent_id"],
        "user_request": record["user_request"],
        "agent_spec": json.dumps(record.get("agent_spec", {}), ensure_ascii=False),
        "system_prompt": record.get("system_prompt", ""),
        "mcp_tools": json.dumps(record.get("mcp_tools", []), ensure_ascii=False),
        "project_files": json.dumps(record.get("project_files", {}), ensure_ascii=False),
        "test_result": json.dumps(record.get("test_result", {}), ensure_ascii=False),
        "graph_structure": json.dumps(record.get("graph_structure", {}), ensure_ascii=False),
        "created_at": record.get("created_at", ""),
        "version": record.get("version", 1),
        "mode": record.get("mode", "solo"),
    }

    client.upsert(
        collection_name=_collection(),
        points=[PointStruct(id=_to_point_id(record["agent_id"]), vector=embedding, payload=payload)],
    )
    log.info("Agent 등록: %s (mode=%s)", record["agent_id"], payload["mode"])


def lookup(
    request_embedding: list[float],
    threshold: float | None = None,
    top_k: int = 1,
) -> list[dict[str, Any]]:
    """요구사항 임베딩 유사도로 기존 에이전트를 검색한다."""
    ensure_collection()
    client = get_client()
    threshold = threshold or settings.meta_registry_similarity_threshold

    response = client.query_points(
        collection_name=_collection(), query=request_embedding, limit=top_k, with_payload=True,
    )

    hits: list[dict[str, Any]] = []
    for point in response.points:
        if point.score < threshold:
            continue
        record = dict(point.payload or {})
        record["score"] = point.score
        hits.append(_parse_json_fields(record))
    return hits


def get(agent_id: str) -> dict[str, Any] | None:
    """agent_id로 레코드를 조회한다. JSON 필드는 파싱."""
    ensure_collection()
    client = get_client()
    points = client.retrieve(
        collection_name=_collection(), ids=[_to_point_id(agent_id)], with_payload=True,
    )
    if not points:
        return None
    return _parse_json_fields(dict(points[0].payload or {}))


def list_all() -> list[dict[str, Any]]:
    """Registry의 모든 레코드를 반환한다 (agent_id, project_files 등 전체 payload)."""
    ensure_collection()
    client = get_client()
    records: list[dict[str, Any]] = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=_collection(), limit=1000, with_payload=True, offset=offset,
        )
        records.extend(dict(p.payload or {}) for p in points)
        if offset is None:
            break
    return records


def delete(agent_id: str) -> bool:
    """에이전트를 Registry에서 삭제한다. 성공 시 True."""
    ensure_collection()
    client = get_client()
    try:
        client.delete(
            collection_name=_collection(),
            points_selector=PointIdsList(points=[_to_point_id(agent_id)]),
        )
        log.info("Agent 삭제: %s", agent_id)
        return True
    except Exception as exc:
        log.error("Agent 삭제 실패: %s — %s", agent_id, exc)
        return False


def update_version(agent_id: str, updated_fields: dict[str, Any]) -> None:
    """기존 에이전트 레코드를 버전업한다 (Dual 모드 재배포 시)."""
    existing = get(agent_id)
    if not existing:
        log.warning("버전업 대상 에이전트 없음: %s", agent_id)
        return

    existing["agent_id"] = agent_id
    existing["version"] = existing.get("version", 1) + 1
    existing.update(updated_fields)

    embedding = embed_texts([existing.get("user_request", "")])[0]
    existing["request_embedding"] = embedding
    register(existing)
    log.info("Agent 버전업: %s → v%d", agent_id, existing["version"])