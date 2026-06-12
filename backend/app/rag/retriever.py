"""Hybrid retriever — semantic search via Milvus with optional keyword boosting."""

from __future__ import annotations

from app.vectordb.milvus_client import embed_texts, search


def hybrid_retrieve(
    query: str,
    top_k: int = 30,
    filter_expr: str | None = None,
) -> list[dict]:
    """Retrieve candidate chunks using Milvus semantic search.

    Returns a list of dicts, each containing:
      id, score, text, source, doc_type, importance, importance_score, color_intensity
    """
    query_vector = embed_texts([query])[0]

    results = search(
        query_vector=query_vector,
        top_k=top_k,
        filter_expr=filter_expr,
        output_fields=[
            "text", "source", "doc_type", "section",
            "importance", "importance_score", "color_intensity",
            "chunk_scores_total",
        ],
    )

    # Boost score by importance (higher importance → slight score boost)
    for r in results:
        imp_score = r.get("importance_score", 0.5)
        r["adjusted_score"] = r.get("score", 0.0) + 0.05 * imp_score

    results.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)

    return results[:top_k]
