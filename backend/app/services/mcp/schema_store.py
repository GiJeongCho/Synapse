"""MCP Schema Store — Qdrant 기반 MCP 도구 명세 저장/검색.

시드 데이터(seed.json)를 로드하고 자연어로 MCP 도구를 검색할 수 있다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.core.logging import logger
from app.vectordb.qdrant_client import _to_point_id, embed_texts, get_client

log = logger(__name__)

_SEED_PATH = Path(__file__).parent / "seed.json"


def _collection() -> str:
    return settings.meta_mcp_collection


def ensure_collection() -> None:
    """MCP 도구 컬렉션이 없으면 생성한다."""
    client = get_client()
    if not client.collection_exists(_collection()):
        client.create_collection(
            collection_name=_collection(),
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )
        log.info("MCP 도구 컬렉션 생성: %s", _collection())


def seed_if_empty() -> int:
    """컬렉션이 비어 있으면 seed.json에서 도구 명세를 로드한다."""
    ensure_collection()
    client = get_client()

    existing, _ = client.scroll(collection_name=_collection(), limit=1)
    if existing:
        return 0

    if not _SEED_PATH.exists():
        log.warning("시드 파일 없음: %s", _SEED_PATH)
        return 0

    tools = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    if not tools:
        return 0

    descriptions = [t["description"] for t in tools]
    vectors = embed_texts(descriptions)

    points = []
    for tool, vec in zip(tools, vectors):
        points.append(
            PointStruct(
                id=_to_point_id(tool["tool_id"]),
                vector=vec,
                payload={
                    "tool_id": tool["tool_id"],
                    "name": tool["name"],
                    "description": tool["description"],
                    "uri": tool.get("uri", ""),
                    "capabilities": json.dumps(tool.get("capabilities", []), ensure_ascii=False),
                    "schema_json": json.dumps(tool.get("schema", {}), ensure_ascii=False),
                    "category": tool.get("category", ""),
                },
            )
        )

    client.upsert(collection_name=_collection(), points=points)
    log.info("MCP 시드 로드 완료: %d개 도구", len(points))
    return len(points)


def search_tools(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """자연어로 MCP 도구를 검색한다."""
    ensure_collection()
    seed_if_empty()
    client = get_client()

    query_vec = embed_texts([query])[0]
    response = client.query_points(
        collection_name=_collection(),
        query=query_vec,
        limit=top_k,
        with_payload=True,
    )

    hits: list[dict[str, Any]] = []
    for point in response.points:
        payload = dict(point.payload or {})
        for field in ("capabilities", "schema_json"):
            val = payload.get(field)
            try:
                payload[field] = json.loads(val) if isinstance(val, str) else val
            except (json.JSONDecodeError, TypeError):
                pass
        hits.append({"score": point.score, **payload})

    return hits