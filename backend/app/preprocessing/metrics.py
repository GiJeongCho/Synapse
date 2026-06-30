"""Five intrinsic chunk-quality metrics from the Adaptive Chunking paper.

RC  — References Completeness  (English only, optional)
BI  — Block Integrity
ICC — Intrachunk Cohesion
DCC — Document Contextual Coherence
SC  — Size Compliance
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import tiktoken

from app.config import settings

_ENC = tiktoken.get_encoding("cl100k_base")


def _token_len(text: str) -> int:
    return len(_ENC.encode(text))


# ---------------------------------------------------------------------------
# Shared embedding helper — lazy-loaded singleton
# ---------------------------------------------------------------------------

def _embed(texts: list[str]) -> np.ndarray:
    """외부 임베딩 API 호출."""
    import httpx
    resp = httpx.post(
        f"{settings.embed_api_url}/embed",
        json={"texts": texts},
        timeout=60.0,
    )
    resp.raise_for_status()
    return np.array(resp.json()["embeddings"], dtype=np.float32)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


# ---------------------------------------------------------------------------
# SC — Size Compliance
# ---------------------------------------------------------------------------

def size_compliance(chunks: list[str]) -> float:
    """Fraction of chunks whose token count falls within [min, max]."""
    if not chunks:
        return 0.0
    compliant = sum(
        1 for c in chunks
        if settings.chunk_min_tokens <= _token_len(c) <= settings.chunk_max_tokens
    )
    return compliant / len(chunks)


# ---------------------------------------------------------------------------
# BI — Block Integrity
# ---------------------------------------------------------------------------

_BLOCK_PATTERNS = [
    re.compile(r"^#{1,6}\s+.+", re.MULTILINE),     # Markdown headings
    re.compile(r"^\|.+\|$", re.MULTILINE),          # Table rows
    re.compile(r"^```", re.MULTILINE),              # Code fences
    re.compile(r"^>\s+", re.MULTILINE),             # Blockquotes
    re.compile(r"제\s*\d+\s*조", re.MULTILINE),     # Korean legal articles
]

_BI_TOLERANCE_CHARS = 5


def _detect_blocks(text: str) -> list[tuple[int, int]]:
    """Detect structural block boundaries as (start, end) char offsets."""
    blocks: list[tuple[int, int]] = []
    for pat in _BLOCK_PATTERNS:
        for m in pat.finditer(text):
            blocks.append((m.start(), m.end()))
    return blocks



def block_integrity(chunks: list[str], original_text: str) -> float:
    """Fraction of structural blocks that are NOT split across chunks."""
    blocks = _detect_blocks(original_text)
    if not blocks:
        return 1.0

    chunk_boundaries: list[int] = []
    offset = 0
    for chunk in chunks:
        idx = original_text.find(chunk[:50], offset)
        if idx == -1:
            idx = offset
        end = idx + len(chunk)
        chunk_boundaries.append(end)
        offset = end

    intact = 0
    for bstart, bend in blocks:
        split = False
        for cb in chunk_boundaries:
            if bstart + _BI_TOLERANCE_CHARS < cb < bend - _BI_TOLERANCE_CHARS:
                split = True
                break
        if not split:
            intact += 1

    return intact / len(blocks)


# ---------------------------------------------------------------------------
# ICC — Intrachunk Cohesion
# ---------------------------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?。])\s+")


def intrachunk_cohesion(chunks: list[str]) -> float:
    """Average cosine similarity between each sentence embedding and its
    parent chunk embedding."""
    if not chunks:
        return 0.0

    scores: list[float] = []
    for chunk in chunks:
        sentences = [s.strip() for s in _SENT_SPLIT.split(chunk) if s.strip()]
        if len(sentences) <= 1:
            scores.append(1.0)
            continue

        all_texts = [chunk] + sentences
        embeddings = _embed(all_texts)
        chunk_emb = embeddings[0]
        sent_embs = embeddings[1:]

        sims = [_cosine_sim(chunk_emb, se) for se in sent_embs]
        scores.append(float(np.mean(sims)))

    return float(np.mean(scores))


# ---------------------------------------------------------------------------
# DCC — Document Contextual Coherence
# ---------------------------------------------------------------------------

_DCC_WINDOW_TOKENS = 3000


def document_contextual_coherence(chunks: list[str], original_text: str) -> float:
    """Average cosine similarity between each chunk and a sliding window of
    surrounding context (up to 3000 tokens)."""
    if len(chunks) <= 1:
        return 1.0

    full_tokens = _ENC.encode(original_text)
    scores: list[float] = []

    token_offset = 0
    for chunk in chunks:
        chunk_tokens = _ENC.encode(chunk)
        chunk_len = len(chunk_tokens)

        window_start = max(0, token_offset - _DCC_WINDOW_TOKENS // 2)
        window_end = min(len(full_tokens), token_offset + chunk_len + _DCC_WINDOW_TOKENS // 2)
        window_text = _ENC.decode(full_tokens[window_start:window_end])

        embeddings = _embed([chunk, window_text])
        scores.append(_cosine_sim(embeddings[0], embeddings[1]))

        token_offset += chunk_len

    return float(np.mean(scores))


# ---------------------------------------------------------------------------
# RC — References Completeness (simplified / optional for non-English)
# ---------------------------------------------------------------------------

_PRONOUN_PATTERN = re.compile(
    r"\b(he|she|it|they|him|her|them|his|its|their|this|that|these|those)\b",
    re.IGNORECASE,
)


def references_completeness(chunks: list[str], original_text: str) -> float:
    """Simplified RC: measures how often pronouns appear in the same chunk
    as their likely antecedent (preceding noun phrase). Full coreference
    resolution (Maverick) requires additional dependencies.

    Returns 1.0 for non-English or when no pronouns are detected."""
    if not any(ord(c) < 128 and c.isalpha() for c in original_text[:500]):
        return 1.0  # skip for non-English

    total_pronouns = 0
    intact = 0

    for chunk in chunks:
        pronouns = _PRONOUN_PATTERN.findall(chunk)
        total_pronouns += len(pronouns)
        words = chunk.split()
        for p in pronouns:
            idx = None
            for i, w in enumerate(words):
                if w.lower().strip(".,;:!?") == p.lower():
                    idx = i
                    break
            if idx is not None and idx > 0:
                intact += 1

    if total_pronouns == 0:
        return 1.0
    return intact / total_pronouns


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

@dataclass
class ChunkMetrics:
    RC: float = 0.0
    BI: float = 0.0
    ICC: float = 0.0
    DCC: float = 0.0
    SC: float = 0.0
    total: float = 0.0

    def as_dict(self) -> dict:
        return {
            "RC": round(self.RC, 4),
            "BI": round(self.BI, 4),
            "ICC": round(self.ICC, 4),
            "DCC": round(self.DCC, 4),
            "SC": round(self.SC, 4),
            "total": round(self.total, 4),
        }


def compute_metrics(
    chunks: list[str],
    original_text: str,
    compute_rc: bool = True,
) -> ChunkMetrics:
    """Compute all 5 intrinsic metrics and return the aggregate."""
    rc = references_completeness(chunks, original_text) if compute_rc else 1.0
    bi = block_integrity(chunks, original_text)
    icc = intrachunk_cohesion(chunks)
    dcc = document_contextual_coherence(chunks, original_text)
    sc = size_compliance(chunks)

    total = (rc + bi + icc + dcc + sc) / 5.0

    return ChunkMetrics(RC=rc, BI=bi, ICC=icc, DCC=dcc, SC=sc, total=total)
