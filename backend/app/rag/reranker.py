"""Reranker — re-scores candidates using cross-encoder or LLM-based relevance."""

from __future__ import annotations

import numpy as np

from app.vectordb.milvus_client import embed_texts


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 10,
) -> list[dict]:
    """Re-rank candidate chunks by computing query-chunk cosine similarity
    with fresh embeddings and combining with the original retrieval score.

    For production, replace with a dedicated cross-encoder model
    (e.g. BAAI/bge-reranker-v2-m3)."""
    if not candidates:
        return []

    texts = [query] + [c.get("text", "") for c in candidates]
    embeddings = embed_texts(texts)
    query_emb = embeddings[0]

    for i, candidate in enumerate(candidates):
        chunk_emb = embeddings[i + 1]
        rerank_score = _cosine_similarity(query_emb, chunk_emb)

        original_score = candidate.get("adjusted_score", candidate.get("score", 0.0))
        candidate["rerank_score"] = rerank_score
        candidate["final_score"] = 0.4 * original_score + 0.6 * rerank_score

    candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    return candidates[:top_k]
