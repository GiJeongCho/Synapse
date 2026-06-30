"""MCP Schema Store — Milvus 기반 MCP 도구 명세 저장/검색.

시드 데이터(seed.json)를 로드하고 자연어로 MCP 도구를 검색할 수 있다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.vectordb.milvus_client import embed_texts, get_client

log = logger(__name__)

_SEED_PATH = Path(__file__).parent / "seed.json"

_OUTPUT_FIELDS = [
    "tool_id",
    "name",
    "description",
    "uri",
    "capabilities",
    "schema_json",
    "category",
]


def _collection() -> str:
    return settings.meta_mcp_collection


def ensure_collection() -> None:
    """MCP 도구 컬렉션이 없으면 생성한다."""
    client = get_client()
    if client.has_collection(_collection()):
        return

    client.create_collection(
        collection_name=_collection(),
        dimension=settings.embedding_dim,
        auto_id=False,
        id_type="string",
        max_length=256,
    )
    log.info("MCP 도구 컬렉션 생성: %s", _collection())


def seed_if_empty() -> int:
    """컬렉션이 비어 있으면 seed.json에서 도구 명세를 로드한다.

    Returns:
        적재된 레코드 수.
    """
    ensure_collection()
    client = get_client()

    existing = client.query(
        collection_name=_collection(),
        filter="",
        output_fields=["tool_id"],
        limit=1,
    )
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

    rows = []
    for tool, vec in zip(tools, vectors):
        rows.append({
            "id": tool["tool_id"],
            "vector": vec,
            "tool_id": tool["tool_id"],
            "name": tool["name"],
            "description": tool["description"],
            "uri": tool.get("uri", ""),
            "capabilities": json.dumps(tool.get("capabilities", []), ensure_ascii=False),
            "schema_json": json.dumps(tool.get("schema", {}), ensure_ascii=False),
            "category": tool.get("category", ""),
        })

    client.upsert(collection_name=_collection(), data=rows)
    log.info("MCP 시드 로드 완료: %d개 도구", len(rows))
    return len(rows)


def search_tools(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """자연어로 MCP 도구를 검색한다."""
    ensure_collection()
    seed_if_empty()
    client = get_client()

    query_vec = embed_texts([query])[0]

    results = client.search(
        collection_name=_collection(),
        data=[query_vec],
        limit=top_k,
        output_fields=_OUTPUT_FIELDS,
    )

    hits: list[dict[str, Any]] = []
    for hit in results[0]:
        entry: dict[str, Any] = {"tool_id": hit["id"], "score": hit["distance"]}
        entity = hit.get("entity", {})
        for field in _OUTPUT_FIELDS:
            val = entity.get(field)
            if field in ("capabilities",):
                try:
                    val = json.loads(val) if isinstance(val, str) else val
                except (json.JSONDecodeError, TypeError):
                    pass
            if field == "schema_json":
                try:
                    val = json.loads(val) if isinstance(val, str) else val
                except (json.JSONDecodeError, TypeError):
                    pass
            entry[field] = val
        hits.append(entry)

    return hits
