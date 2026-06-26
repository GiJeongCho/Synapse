"""Agent Registry — Milvus 기반 CRUD.

생성된 에이전트를 저장하고 요구사항 유사도로 기존 에이전트를 검색한다.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pymilvus import MilvusClient

from app.core.config import settings
from app.core.logging import logger
from app.vectordb.milvus_client import embed_texts, get_client

log = logger(__name__)

_FIELDS = [
    "agent_id",
    "user_request",
    "agent_spec",
    "system_prompt",
    "mcp_tools",
    "project_files",
    "test_result",
    "graph_structure",
    "created_at",
    "version",
    "mode",
]


def _collection() -> str:
    return settings.meta_registry_collection


def ensure_collection() -> None:
    """Agent Registry 컬렉션이 없으면 생성하고, 항상 로드 상태를 보장한다."""
    client = get_client()
    if client.has_collection(_collection()):
        try:
            client.load_collection(_collection())
        except Exception:
            pass
        return

    client.create_collection(
        collection_name=_collection(),
        dimension=settings.embedding_dim,
        auto_id=False,
        id_type="string",
        max_length=256,
    )
    client.load_collection(_collection())
    log.info("Agent Registry 컬렉션 생성: %s", _collection())


def register(record: dict[str, Any]) -> None:
    """에이전트 레코드를 Registry에 저장한다."""
    ensure_collection()
    client = get_client()

    embedding = record.get("request_embedding")
    if not embedding:
        embedding = embed_texts([record["user_request"]])[0]

    row: dict[str, Any] = {
        "id": record["agent_id"],
        "vector": embedding,
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

    client.upsert(collection_name=_collection(), data=[row])
    log.info("Agent 등록: %s (mode=%s)", record["agent_id"], row["mode"])


def lookup(
    request_embedding: list[float],
    threshold: float | None = None,
    top_k: int = 1,
) -> list[dict[str, Any]]:
    """요구사항 임베딩 유사도로 기존 에이전트를 검색한다."""
    ensure_collection()
    client = get_client()
    threshold = threshold or settings.meta_registry_similarity_threshold

    results = client.search(
        collection_name=_collection(),
        data=[request_embedding],
        limit=top_k,
        output_fields=_FIELDS,
    )

    hits: list[dict[str, Any]] = []
    for hit in results[0]:
        score = hit["distance"]
        if score < threshold:
            continue
        entry = {"agent_id": hit["id"], "score": score}
        entity = hit.get("entity", {})
        for field in _FIELDS:
            val = entity.get(field)
            if field in ("agent_spec", "mcp_tools", "project_files", "test_result", "graph_structure"):
                try:
                    val = json.loads(val) if isinstance(val, str) else val
                except (json.JSONDecodeError, TypeError):
                    pass
            entry[field] = val
        hits.append(entry)

    return hits


def get(agent_id: str) -> dict[str, Any] | None:
    """agent_id(Milvus id 또는 agent_id 필드)로 레코드를 조회한다. JSON 필드는 파싱."""
    ensure_collection()
    client = get_client()

    results = client.query(
        collection_name=_collection(),
        filter=f'id == "{agent_id}"',
        output_fields=_FIELDS,
        limit=1,
    )
    if not results:
        results = client.query(
            collection_name=_collection(),
            filter=f'agent_id == "{agent_id}"',
            output_fields=_FIELDS,
            limit=1,
        )
    if not results:
        return None

    record = results[0]
    for field in ("agent_spec", "mcp_tools", "project_files", "test_result", "graph_structure"):
        val = record.get(field)
        if isinstance(val, str):
            try:
                record[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
    return record


def delete(agent_id: str) -> bool:
    """에이전트를 Registry에서 삭제한다. 성공 시 True."""
    ensure_collection()
    client = get_client()

    try:
        client.delete(collection_name=_collection(), ids=[agent_id])
        log.info("Agent 삭제: %s", agent_id)
        return True
    except Exception as exc:
        log.error("Agent 삭제 실패: %s — %s", agent_id, exc)
        return False


def update_version(agent_id: str, updated_fields: dict[str, Any]) -> None:
    """기존 에이전트 레코드를 버전업한다 (Dual 모드 재배포 시)."""
    ensure_collection()
    client = get_client()

    existing = client.query(
        collection_name=_collection(),
        filter=f'id == "{agent_id}"',
        output_fields=_FIELDS,
    )
    if not existing:
        log.warning("버전업 대상 에이전트 없음: %s", agent_id)
        return

    record = existing[0]
    record["agent_id"] = agent_id
    record["version"] = record.get("version", 1) + 1
    record.update(updated_fields)

    embedding = embed_texts([record.get("user_request", "")])[0]
    record["request_embedding"] = embedding
    register(record)
    log.info("Agent 버전업: %s → v%d", agent_id, record["version"])
