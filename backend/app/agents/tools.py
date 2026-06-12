"""Tool definitions for LangGraph agents — wrappers around core modules."""

from __future__ import annotations

from typing import Any

from app.graph.neo4j_client import get_document_graph, get_related_concepts
from app.rag.retriever import hybrid_retrieve
from app.rag.reranker import rerank


def tool_search(query: str, top_k: int = 10, doc_type: str | None = None) -> list[dict]:
    """Search Milvus for relevant chunks and rerank."""
    filter_expr = f'doc_type == "{doc_type}"' if doc_type else None
    candidates = hybrid_retrieve(query=query, top_k=top_k * 3, filter_expr=filter_expr)
    return rerank(query=query, candidates=candidates, top_k=top_k)


def tool_graph_explore(concept: str, max_depth: int = 2) -> list[dict]:
    """Explore Neo4j graph for related concepts and documents."""
    try:
        return get_related_concepts(concept, max_depth=max_depth)
    except Exception:
        return []


def tool_graph_document(source: str) -> dict:
    """Get the knowledge graph for a specific document."""
    try:
        return get_document_graph(source)
    except Exception:
        return {"nodes": [], "edges": []}
