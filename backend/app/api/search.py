"""API endpoints for RAG search and reranking."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.retriever import hybrid_retrieve
from app.rag.reranker import rerank

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    doc_type_filter: str | None = None
    importance_filter: str | None = None  # "core", "support", etc.


class SearchResponse(BaseModel):
    query: str
    results: list[dict]
    total: int


@router.post("/query", response_model=SearchResponse)
async def search_query(req: SearchRequest):
    """Search for relevant chunks using hybrid retrieval + reranking."""
    filter_expr = _build_filter(req.doc_type_filter, req.importance_filter)

    candidates = hybrid_retrieve(
        query=req.query,
        top_k=req.top_k * 3,
        filter_expr=filter_expr,
    )

    reranked = rerank(query=req.query, candidates=candidates, top_k=req.top_k)

    return SearchResponse(
        query=req.query,
        results=reranked,
        total=len(reranked),
    )


def _build_filter(doc_type: str | None, importance: str | None) -> str | None:
    parts: list[str] = []
    if doc_type:
        parts.append(f'doc_type == "{doc_type}"')
    if importance:
        parts.append(f'importance == "{importance}"')
    return " and ".join(parts) if parts else None
