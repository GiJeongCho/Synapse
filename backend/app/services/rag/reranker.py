"""검색 결과 리랭킹.

외부 Reranker API를 호출하고, 실패 시 점수 기반 폴백으로 재정렬한다.
"""

from __future__ import annotations

from typing import List

import httpx

from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)


def rerank(query: str, candidates: List[dict], top_k: int = 10) -> List[dict]:
    """외부 reranker API로 재정렬. 실패 시 점수 기반 폴백."""
    texts = [c.get("text", "") for c in candidates]

    try:
        resp = httpx.post(
            f"{settings.rerank_api_url}/rerank",
            json={"query": query, "texts": texts, "top_k": top_k},
            timeout=30.0,
        )
        resp.raise_for_status()
        ranked = resp.json()["results"]
        reranked = []
        for item in ranked:
            idx = item["index"]
            c = candidates[idx].copy()
            c["final_score"] = item["score"]
            reranked.append(c)
        return reranked[:top_k]

    except Exception as e:
        log.warning(f"Reranker API 실패, 폴백 사용: {e}")
        qw = settings.quality_weight
        iw = settings.importance_weight
        for c in candidates:
            base = float(c.get("score", 0.0))
            intensity = float(c.get("color_intensity", 0.5))
            c["final_score"] = round(iw * base + qw * intensity, 6)
        candidates.sort(key=lambda c: c.get("final_score", 0.0), reverse=True)
        return candidates[:top_k]