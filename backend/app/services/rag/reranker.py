"""검색 결과 리랭킹.

1순위: 외부 FastAPI rerank API (settings.rerank_api_url) 호출.
API 미응답/미로드 시 검색점수·품질/중요도(color_intensity) 가중합으로 폴백.
"""

from __future__ import annotations
from typing import List
import httpx
from app.config import settings
from app.core.logging import logger

log = logger(__name__)


def _rerank_via_api(query: str, candidates: List[dict], top_k: int) -> List[dict] | None:
    documents = [c.get("text", "") for c in candidates]
    url = f"{settings.rerank_api_url.rstrip('/')}/rerank"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json={"query": query, "documents": documents})
            resp.raise_for_status()
        results = resp.json()
        ranked = sorted(results, key=lambda r: r.get("score", 0.0), reverse=True)
        reranked: List[dict] = []
        for r in ranked[:top_k]:
            item = candidates[r["index"]].copy()
            item["final_score"] = round(float(r.get("score", 0.0)), 6)
            reranked.append(item)
        return reranked
    except Exception as exc:
        log.warning("[Reranker] API 호출 실패, 폴백 사용: %s", exc)
        return None


def rerank(query: str, candidates: List[dict], top_k: int = 10) -> List[dict]:
    api_result = _rerank_via_api(query, candidates, top_k)
    if api_result is not None:
        return api_result

    qw = settings.quality_weight
    iw = settings.importance_weight
    for c in candidates:
        base = float(c.get("score", 0.0))
        intensity = float(c.get("color_intensity", 0.5))
        c["final_score"] = round(iw * base + qw * intensity, 6)
    candidates.sort(key=lambda c: c.get("final_score", 0.0), reverse=True)
    return candidates[:top_k]
