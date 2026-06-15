"""검색 결과 리랭킹.

검색 점수와 청크 품질/중요도(color_intensity)를 결합해 재정렬한다.
가중치는 ``settings.quality_weight`` / ``settings.importance_weight``.
"""

from __future__ import annotations

from typing import List

from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)


def rerank(query: str, candidates: List[dict], top_k: int = 10) -> List[dict]:
    """후보를 (검색점수 × 품질가중) 으로 재정렬해 상위 top_k 를 반환한다."""
    _ = query  # 시맨틱 재계산은 cross-encoder 도입 시 사용(TODO)
    qw = settings.quality_weight
    iw = settings.importance_weight

    for c in candidates:
        base = float(c.get("score", 0.0))
        intensity = float(c.get("color_intensity", 0.5))
        c["final_score"] = round(iw * base + qw * intensity, 6)

    candidates.sort(key=lambda c: c.get("final_score", 0.0), reverse=True)
    return candidates[:top_k]
