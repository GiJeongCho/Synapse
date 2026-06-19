"""Document type classifier — routes documents to the optimal chunker."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from anthropic import Anthropic

from app.config import settings


class DocType(str, Enum):
    PAPER = "paper"
    NEWS = "news"
    LAW = "law"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    doc_type: DocType
    confidence: float
    reason: str


_HEURISTIC_PATTERNS: dict[DocType, list[re.Pattern]] = {
    DocType.PAPER: [
        re.compile(r"(?i)\babstract\b"),
        re.compile(r"(?i)\breferences?\b\s*$", re.MULTILINE),
        re.compile(r"(?i)\barxiv\b"),
        re.compile(r"(?i)\bintroduction\b"),
        re.compile(r"(?i)\bmethod(?:ology)?\b"),
        re.compile(r"\b\d{4}\.\d{4,5}\b"),  # arXiv ID pattern
    ],
    DocType.LAW: [
        re.compile(r"제\s*\d+\s*조"),
        re.compile(r"제\s*\d+\s*[장절]"),       # 제1장, 제2절
        re.compile(r"규정\s*제\d+호"),            # 규정 제600호
        re.compile(r"(?i)\b(?:article|section)\s+\d+"),
        re.compile(r"(?i)\b법률\b"),
        re.compile(r"(?i)\b시행령\b"),
        re.compile(r"(?i)\b조항\b"),
        re.compile(r"(?i)\bstatute\b"),
    ],
    DocType.NEWS: [
        re.compile(r"(?i)\b기자\b"),
        re.compile(r"(?i)\b특파원\b"),
        re.compile(r"(?i)\breporter\b"),
        re.compile(r"(?i)\b뉴스\b"),
    ],
}

_MIN_HITS_FOR_CONFIDENCE = 3


def classify_by_heuristic(text: str) -> ClassificationResult:
    """Fast heuristic classification based on regex pattern matching."""
    preview = text[:5000]
    scores: dict[DocType, int] = {dt: 0 for dt in DocType if dt != DocType.UNKNOWN}

    for doc_type, patterns in _HEURISTIC_PATTERNS.items():
        for pat in patterns:
            if pat.search(preview):
                scores[doc_type] += 1

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best]

    if best_score == 0:
        return ClassificationResult(DocType.UNKNOWN, 0.0, "no heuristic match")

    confidence = min(best_score / _MIN_HITS_FOR_CONFIDENCE, 1.0)
    return ClassificationResult(best, confidence, f"heuristic hits={best_score}")


async def classify_by_llm(text: str) -> ClassificationResult:
    """LLM-based classification for ambiguous documents."""
    client = Anthropic(api_key=settings.anthropic_api_key)
    preview = text[:4000]

    message = client.messages.create(
        model=settings.llm_model,
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": (
                    "Classify this document as exactly one of: paper, news, law.\n"
                    "Reply in JSON: {\"type\": \"...\", \"confidence\": 0.0-1.0, \"reason\": \"...\"}\n\n"
                    f"--- DOCUMENT PREVIEW ---\n{preview}"
                ),
            }
        ],
    )
    import json

    try:
        raw = message.content[0].text.strip()
        # Handle markdown code blocks
        if raw.startswith("```"):
            raw = re.sub(r"```\w*\n?", "", raw).strip()
        result = json.loads(raw)
        return ClassificationResult(
            doc_type=DocType(result["type"]),
            confidence=float(result["confidence"]),
            reason=result.get("reason", "llm"),
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return ClassificationResult(DocType.UNKNOWN, 0.0, "llm parse failure")


async def classify(text: str, llm_fallback: bool = True) -> ClassificationResult:
    """Classify document type: heuristic first, LLM fallback if ambiguous."""
    result = classify_by_heuristic(text)
    if result.confidence >= 0.7:
        return result

    if llm_fallback and settings.anthropic_api_key:
        return await classify_by_llm(text)

    return result
