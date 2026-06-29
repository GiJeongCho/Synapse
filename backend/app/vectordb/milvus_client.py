"""Milvus vector DB client — collection schema, upsert, search, delete.

Uses MilvusClient (works with both Milvus Lite local .db and remote server).
Embedding is delegated to the external FastAPI embed service (settings.embed_api_url)."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("GRPC_KEEPALIVE_TIME_MS", "120000")
os.environ.setdefault("GRPC_KEEPALIVE_PERMIT_WITHOUT_CALLS", "0")

import httpx
from pymilvus import MilvusClient

from app.config import settings

_client: MilvusClient | None = None


def get_client() -> MilvusClient:
    global _client
    if _client is None:
        _client = MilvusClient(uri=settings.milvus_uri)
    return _client


def ensure_collection() -> None:
    """Create the collection if it does not already exist."""
    client = get_client()
    if client.has_collection(settings.milvus_collection):
        return

    client.create_collection(
        collection_name=settings.milvus_collection,
        dimension=settings.embedding_dim,
        auto_id=False,
        id_type="string",
        max_length=256,
    )


# ---------------------------------------------------------------------------
# Embedding helper — external FastAPI service
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str]) -> list[list[float]]:
    """외부 임베딩 API 호출하여 벡터 반환."""
    import httpx
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
    """Insert or update chunks with their embeddings and metadata."""
    ensure_collection()
    client = get_client()

    data = []
    for cid, text, vec, payload in zip(chunk_ids, texts, vectors, payloads):
        row = {
            "id": cid,
            "vector": vec,
            "text": text,
            **payload,
        }
        data.append(row)

    client.upsert(collection_name=settings.milvus_collection, data=data)


def search(
    query_vector: list[float],
    top_k: int = 10,
    filter_expr: str | None = None,
    output_fields: list[str] | None = None,
) -> list[dict]:
    """Semantic similarity search. Returns list of hit dicts."""
    ensure_collection()
    client = get_client()

    if output_fields is None:
        output_fields = ["text", "source", "doc_type", "importance", "importance_score", "color_intensity"]

    results = client.search(
        collection_name=settings.milvus_collection,
        data=[query_vector],
        limit=top_k,
        filter=filter_expr or "",
        output_fields=output_fields,
    )

    hits: list[dict] = []
    for hit in results[0]:
        entry = {"id": hit["id"], "score": hit["distance"]}
        entry.update(hit.get("entity", {}))
        hits.append(entry)
    return hits


def delete_chunks(chunk_ids: list[str]) -> None:
    """Delete chunks by ID."""
    client = get_client()
    client.delete(
        collection_name=settings.milvus_collection,
        ids=chunk_ids,
    )


def get_chunks_by_source(source: str) -> list[dict]:
    """Retrieve all chunks belonging to a specific document source."""
    ensure_collection()
    client = get_client()

    results = client.query(
        collection_name=settings.milvus_collection,
        filter=f'source == "{source}"',
        output_fields=[
            "text", "source", "doc_type", "section",
            "chunk_scores_total", "chunker_used",
            "importance", "importance_score", "color_intensity",
            "user_adjusted",
        ],
    )
    return results


def list_sources() -> list[dict]:
    """List distinct document sources in the collection."""
    ensure_collection()
    client = get_client()

    results = client.query(
        collection_name=settings.milvus_collection,
        filter="",
        output_fields=["source", "doc_type"],
        limit=1000,
    )

    seen: dict[str, str] = {}
    for r in results:
        src = r.get("source", "")
        if src and src not in seen:
            seen[src] = r.get("doc_type", "unknown")

    return [{"source": s, "doc_type": dt} for s, dt in seen.items()]

    

def drop_all_chunks() -> None:
    """컬렉션 전체 삭제 후 재생성."""
    client = get_client()
    if client.has_collection(settings.milvus_collection):
        client.drop_collection(settings.milvus_collection)
    ensure_collection()


def delete_chunks_by_source(source: str) -> None:
    client = get_client()
    client.delete(
        collection_name=settings.milvus_collection,
        filter=f'source == "{source}"',
    )