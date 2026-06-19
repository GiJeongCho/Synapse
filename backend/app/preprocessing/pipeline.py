"""Preprocessing pipeline orchestrator — ties together classification,
chunking, metrics, normalisation, scoring, embedding, and storage."""

from __future__ import annotations

import hashlib
import os
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
from app.vectordb.milvus_client import embed_texts, upsert_chunks


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


def _chunk_id(source: str, idx: int) -> str:
    h = hashlib.md5(source.encode()).hexdigest()[:8]
    return f"chunk_{h}_{idx:04d}"


_SECTION_PATTERNS: dict[str, list[str]] = {
    "law": [
        r"제\s*\d+\s*[장절]\s+(.+)",   # 제1장 총칙, 제2절 감사인의 의무
    ],
    "report": [
        r"^[IVX]+\.\s+(.+)",            # I. 서론
        r"^\d+\.\s+(.+)",               # 1. 개요
    ],
    "manual": [
        r"^\d+\.\d+\s+(.+)",            # 1.1 설치 방법
    ],
}

_ENGLISH_SECTIONS = [
    "abstract", "introduction", "method", "methodology",
    "results", "discussion", "conclusion", "references", "acknowledgement",
]

def _detect_section(chunk_text: str, doc_type: str = "paper") -> str | None:
    """Try to detect which section a chunk belongs to from its content."""
    import re

    for pattern in _SECTION_PATTERNS.get(doc_type, []):
        match = re.search(pattern, chunk_text, re.MULTILINE)
        if match:
            return match.group(1).strip()

    heading = re.search(r"^#{1,3}\s+(.+)", chunk_text, re.MULTILINE)
    if heading:
        return heading.group(1).strip().lower()

    for section_name in _ENGLISH_SECTIONS:
        if section_name in chunk_text[:200].lower():
            return section_name

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

    for name, chunks in candidates.items():
        if not chunks:
            continue
        normalized = normalize_chunks(chunks)
        metrics = compute_metrics(normalized, text, compute_rc=True)
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
    for i, chunk_text in enumerate(best_chunks):
        section = _detect_section(chunk_text, doc_type=doc_type.value)
        importance = score_chunk_sync(
            chunk_text,
            section=section,
            doc_type=doc_type.value,
            quality_total=best_metrics.total,
        )
        cid = _chunk_id(source, i)
        per_chunk_metrics = compute_metrics([chunk_text], text, compute_rc=False)

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

    return PipelineResult(
        source=source,
        doc_type=doc_type.value,
        chunker_used=best_chunker,
        chunks=processed,
        metrics_summary=best_metrics.as_dict(),
    )


def reembed_and_upsert(chunk_id: str, new_text: str, source: str, doc_type: str) -> dict:
    """Re-embed a single edited chunk and upsert it back to Milvus."""
    vectors = embed_texts([new_text])
    section = _detect_section(new_text, doc_type=doc_type)

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
