"""Preprocessing pipeline orchestrator — ties together classification,
chunking, metrics, normalisation, scoring, embedding, and storage."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.preprocessing.classifier import DocType, classify
from app.preprocessing.chunkers.llm_regex import llm_regex_split
from app.preprocessing.chunkers.recursive import recursive_split
from app.preprocessing.chunkers.split_merge import (
    split_then_merge,
    split_then_merge_legal,
)
from app.preprocessing.metrics import ChunkMetrics, compute_metrics
from app.preprocessing.normalize import normalize_chunks
from app.preprocessing.scoring import ImportanceResult, score_chunk_sync
# from app.vectordb.milvus_client import embed_texts, upsert_chunks
from app.vectordb.qdrant_client import embed_texts, upsert_chunks


@dataclass
class ProcessedChunk:
    chunk_id: str
    text: str
    metrics: ChunkMetrics
    importance: ImportanceResult
    section: str | None = None


@dataclass
class PipelineResult:
    source: str
    doc_type: str
    chunker_used: str
    chunks: list[ProcessedChunk]
    metrics_summary: dict[str, float]
    all_chunker_metrics: dict[str, dict[str, float]] = None


def _chunk_id(source: str, idx: int) -> str:
    h = hashlib.md5(source.encode()).hexdigest()[:8]
    return f"chunk_{h}_{idx:04d}"


_ARTICLE_RE = re.compile(r'제\s*(\d+)\s*조\s*[\(（]?([^\)\n）]{0,20})')

def _extract_article_info(chunk_text: str) -> dict | None:
    """법률 청크의 첫 300자에서 조문 번호와 제목을 추출한다."""
    m = _ARTICLE_RE.search(chunk_text[:300])
    if m:
        article_no = f"제{m.group(1)}조"
        title = m.group(2).strip().rstrip("）)") if m.group(2) else None
        return {"article_no": article_no, "title": title}
    return None


_SECTION_PATTERNS = {
    "law": [
        (r"제\s*(\d+)\s*장\s*(.+)", "장"),
        (r"제\s*(\d+)\s*절\s*(.+)", "절"),
        (r"제\s*(\d+)\s*조", "조"),
    ],
    "paper": [
        (r"^#{1,3}\s+(.+)", None),
    ],
    "news": [],
}

def _detect_section(chunk_text: str, doc_type: str = "paper") -> str | None:
    import re
    patterns = _SECTION_PATTERNS.get(doc_type, [])
    for pattern, label in patterns:
        m = re.search(pattern, chunk_text[:300], re.MULTILINE)
        if m:
            return m.group(0).strip()

    # 영어 섹션명 폴백
    for name in ["abstract", "introduction", "background", "related work",
                 "method", "results", "discussion", "conclusion",
                 "acknowledgement", "references", "appendix"]:
        if name in chunk_text[:200].lower():
            return name
    return None


async def run_pipeline(
    text: str,
    source: str,
    use_llm_chunker: bool = True,
    use_llm_scoring: bool = False,
) -> PipelineResult:
    """Execute the full preprocessing pipeline:
    1. Classify document type
    2. Run candidate chunkers
    3. Score each candidate with 5 intrinsic metrics
    4. Pick the best chunker per document
    5. Normalise chunk sizes
    6. Score importance → color_intensity
    7. Embed and store in Milvus
    """

    # --- 1. Classification ---
    classification = await classify(text, llm_fallback=use_llm_chunker)
    doc_type = classification.doc_type

    # --- 2. Run candidate chunkers ---
    candidates: dict[str, list[str]] = {}

    candidates["recursive"] = recursive_split(text)
    candidates["split_merge"] = (
        split_then_merge_legal(text) if doc_type == DocType.LAW else split_then_merge(text)
    )

    if use_llm_chunker and doc_type in (DocType.PAPER, DocType.LAW):
        try:
            candidates["llm_regex"] = await llm_regex_split(text)
        except Exception:
            pass  # fallback to other chunkers

    # --- 3. Score each candidate ---
    best_chunker = ""
    best_score = -1.0
    best_metrics: ChunkMetrics | None = None
    best_chunks: list[str] = []
    all_chunker_metrics: dict[str, dict] = {} 
    
    for name, chunks in candidates.items():
        if not chunks:
            continue
        normalized = normalize_chunks(chunks)
        metrics = compute_metrics(normalized, text, compute_rc=True)
        all_chunker_metrics[name] = metrics.as_dict() 
        if metrics.total > best_score:
            best_score = metrics.total
            best_chunker = name
            best_metrics = metrics
            best_chunks = normalized

    if not best_chunks:
        best_chunks = [text]
        best_chunker = "full_document"
        best_metrics = compute_metrics(best_chunks, text)

    # --- 4. Score importance for each chunk ---
    processed: list[ProcessedChunk] = []
    article_map: list[dict] = []
    last_section = None
    for i, chunk_text in enumerate(best_chunks):
        section = _detect_section(chunk_text, doc_type.value)
        if section:
            last_section = section   # 새 섹션 발견하면 갱신
        else:
            section = last_section   # 없으면 이전 섹션 유지
        importance = score_chunk_sync(
            chunk_text,
            section=section,
            doc_type=doc_type.value,
            quality_total=best_metrics.total,
        )
        cid = _chunk_id(source, i)
        per_chunk_metrics = compute_metrics([chunk_text], text, compute_rc=False)

        article_info = _extract_article_info(chunk_text) if doc_type == DocType.LAW else None
        article_map.append({
            "chunk_id": cid,
            "article_no": article_info["article_no"] if article_info else None,
            "title": article_info["title"] if article_info else None,
        })

        processed.append(ProcessedChunk(
            chunk_id=cid,
            text=chunk_text,
            metrics=per_chunk_metrics,
            importance=importance,
            section=section,
        ))

    # --- 5. Embed and store ---
    texts = [p.text for p in processed]
    vectors = embed_texts(texts)

    chunk_ids = [p.chunk_id for p in processed]
    payloads: list[dict[str, Any]] = []
    for p in processed:
        payloads.append({
            "source": source,
            "doc_type": doc_type.value,
            "section": p.section or "",
            "chunk_scores_total": p.metrics.total,
            "chunker_used": best_chunker,
            "importance": p.importance.label.value,
            "importance_score": p.importance.score,
            "importance_reason": p.importance.reason,
            "color_intensity": p.importance.color_intensity,
            "user_adjusted": False,
        })

    

    upsert_chunks(chunk_ids, texts, vectors, payloads)

    from app.services.rag.graph_store import graph_store
    graph_store.upsert_document_chunks(
        source=source,
        doc_type=doc_type.value,
        chunk_ids=chunk_ids,
        sections=[p.section or "" for p in processed],
        article_map=article_map,
    )

    return PipelineResult(
        source=source,
        doc_type=doc_type.value,
        chunker_used=best_chunker,
        chunks=processed,
        metrics_summary=best_metrics.as_dict(),
        all_chunker_metrics=all_chunker_metrics,
    )


def reembed_and_upsert(chunk_id: str, new_text: str, source: str, doc_type: str) -> dict:
    """Re-embed a single edited chunk and upsert it back to Milvus."""
    vectors = embed_texts([new_text])
    section = _detect_section(new_text, doc_type)

    per_chunk_metrics = compute_metrics([new_text], new_text, compute_rc=False)
    importance = score_chunk_sync(
        new_text,
        section=section,
        doc_type=doc_type,
        quality_total=per_chunk_metrics.total,
    )

    payload = {
        "source": source,
        "doc_type": doc_type,
        "section": section or "",
        "chunk_scores_total": per_chunk_metrics.total,
        "chunker_used": "user_edited",
        "importance": importance.label.value,
        "importance_score": importance.score,
        "importance_reason": importance.reason + ", user_edited",
        "color_intensity": importance.color_intensity,
        "user_adjusted": True,
    }

    upsert_chunks([chunk_id], [new_text], vectors, [payload])


    return {
        "chunk_id": chunk_id,
        "importance": importance.label.value,
        "importance_score": importance.score,
        "color_intensity": importance.color_intensity,
        "metrics": per_chunk_metrics.as_dict(),
    }
