"""Importance scoring — assigns Core / Support / Context / Noise labels
and computes a combined color_intensity (0–1) for HITL visualisation.

This module goes BEYOND the Adaptive Chunking paper by adding LLM-based
importance classification and domain-aware keyword density."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.config import settings


class ImportanceLabel(str, Enum):
    CORE = "core"
    SUPPORT = "support"
    CONTEXT = "context"
    NOISE = "noise"


@dataclass
class ImportanceResult:
    label: ImportanceLabel
    score: float          # 0–1
    reason: str
    color_intensity: float  # 0–1 (combined quality + importance)


# ---------------------------------------------------------------------------
# Position weight
# ---------------------------------------------------------------------------

_SECTION_WEIGHTS: dict[str, float] = {
    "abstract": 0.3,
    "conclusion": 0.3,
    "results": 0.2,
    "discussion": 0.2,
    "introduction": 0.1,
    "method": 0.1,
    "methodology": 0.1,
    "background": 0.0,
    "related work": 0.0,
    "acknowledgement": -0.5,
    "acknowledgements": -0.5,
    "appendix": -0.2,
    "references": -0.5,
}


def _position_weight(text: str, section: str | None = None) -> float:
    """Bonus/penalty based on which section the chunk likely belongs to."""
    if section:
        for key, weight in _SECTION_WEIGHTS.items():
            if key in section.lower():
                return weight

    lower = text[:200].lower()
    for key, weight in _SECTION_WEIGHTS.items():
        if key in lower:
            return weight
    return 0.0


# ---------------------------------------------------------------------------
# Keyword density
# ---------------------------------------------------------------------------

_PAPER_KEYWORDS = [
    "propose", "outperform", "novel", "state-of-the-art", "sota",
    "result", "achieve", "significant", "demonstrate", "improve",
    "contribution", "finding", "제안", "성능", "결과", "향상",
]

_LAW_KEYWORDS = [
    "의무", "금지", "벌칙", "처벌", "위반", "shall", "must", "prohibit",
    "제재", "조항", "규정", "시행", "적용",
]

_NEWS_KEYWORDS = [
    "발표", "보도", "밝혔다", "전했다", "예정", "계획", "announced",
    "reported", "breaking",
]


def _keyword_density(text: str, doc_type: str = "paper") -> float:
    """Normalised keyword density score (0–1)."""
    keywords = {
        "paper": _PAPER_KEYWORDS,
        "law": _LAW_KEYWORDS,
        "news": _NEWS_KEYWORDS,
    }.get(doc_type, _PAPER_KEYWORDS)

    lower = text.lower()
    words = lower.split()
    if not words:
        return 0.0

    hits = sum(1 for kw in keywords if kw.lower() in lower)
    density = hits / len(keywords)
    return min(density, 1.0)


# ---------------------------------------------------------------------------
# Citation density (papers only)
# ---------------------------------------------------------------------------

_CITATION_PATTERN = re.compile(r"\[(\d+(?:,\s*\d+)*)\]")


def _citation_density(text: str) -> float:
    """Normalised count of inline citations like [1], [2,3]."""
    matches = _CITATION_PATTERN.findall(text)
    count = sum(len(m.split(",")) for m in matches)
    return min(count / 10.0, 1.0)


# ---------------------------------------------------------------------------
# LLM-based binary classification (optional, requires API key)
# ---------------------------------------------------------------------------

async def _llm_is_core(text: str) -> tuple[bool, str]:
    """Ask LLM whether this chunk contains a core claim or conclusion."""
    if not settings.anthropic_api_key:
        return False, "no_api_key"

    from anthropic import Anthropic
    import json

    client = Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.llm_model,
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": (
                    "Does this text chunk contain a core claim, key finding, or "
                    "conclusion? Reply JSON: {\"is_core\": true/false, \"reason\": \"...\"}\n\n"
                    f"{text[:1500]}"
                ),
            }
        ],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```\w*\n?", "", raw).strip()
    try:
        result = json.loads(raw)
        return result.get("is_core", False), result.get("reason", "")
    except (json.JSONDecodeError, KeyError):
        return False, "parse_error"


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def _classify_label(score: float) -> ImportanceLabel:
    if score >= 0.7:
        return ImportanceLabel.CORE
    if score >= 0.4:
        return ImportanceLabel.SUPPORT
    if score >= 0.15:
        return ImportanceLabel.CONTEXT
    return ImportanceLabel.NOISE


def score_chunk_sync(
    text: str,
    section: str | None = None,
    doc_type: str = "paper",
    quality_total: float = 0.5,
) -> ImportanceResult:
    """Synchronous scoring without LLM — uses heuristics only."""
    pos_w = _position_weight(text, section)
    kw_d = _keyword_density(text, doc_type)
    cit_d = _citation_density(text) if doc_type == "paper" else 0.0

    # importance = weighted combination (0–1 range)
    raw_importance = 0.3 + pos_w + 0.3 * kw_d + 0.2 * cit_d
    importance_score = max(0.0, min(1.0, raw_importance))

    label = _classify_label(importance_score)

    color_intensity = (
        settings.quality_weight * quality_total
        + settings.importance_weight * importance_score
    )
    color_intensity = max(0.0, min(1.0, color_intensity))

    reason_parts = [f"pos={pos_w:+.1f}", f"kw={kw_d:.2f}"]
    if doc_type == "paper":
        reason_parts.append(f"cit={cit_d:.2f}")

    return ImportanceResult(
        label=label,
        score=importance_score,
        reason=", ".join(reason_parts),
        color_intensity=color_intensity,
    )


async def score_chunk(
    text: str,
    section: str | None = None,
    doc_type: str = "paper",
    quality_total: float = 0.5,
    use_llm: bool = False,
) -> ImportanceResult:
    """Full scoring pipeline — optional LLM binary classification."""
    result = score_chunk_sync(text, section, doc_type, quality_total)

    if use_llm and settings.anthropic_api_key:
        is_core, reason = await _llm_is_core(text)
        if is_core:
            result.score = min(1.0, result.score + 0.25)
            result.label = _classify_label(result.score)
            result.reason += f", llm_core={reason}"
            result.color_intensity = (
                settings.quality_weight * quality_total
                + settings.importance_weight * result.score
            )
            result.color_intensity = max(0.0, min(1.0, result.color_intensity))

    return result
