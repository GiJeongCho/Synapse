"""Agent Registry 유사도 매칭.

요구사항 텍스트를 임베딩하여 Registry에서 가장 유사한 기존 에이전트를 찾는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import logger
from app.services.agent_registry import store
from app.vectordb.milvus_client import embed_texts

log = logger(__name__)


@dataclass
class MatchResult:
    """Registry 매칭 결과."""

    hit: bool
    agent: Optional[dict[str, Any]]
    similarity: float


def match_request(user_request: str) -> MatchResult:
    """요구사항을 임베딩하여 Registry에서 매칭한다.

    Returns:
        MatchResult: hit=True이면 agent에 기존 에이전트 정보가 담긴다.
    """
    embedding = embed_texts([user_request])[0]
    threshold = settings.meta_registry_similarity_threshold

    hits = store.lookup(embedding, threshold=threshold, top_k=1)

    if hits:
        best = hits[0]
        log.info(
            "Registry HIT: agent=%s, similarity=%.3f (threshold=%.2f)",
            best["agent_id"],
            best["score"],
            threshold,
        )
        return MatchResult(hit=True, agent=best, similarity=best["score"])

    log.info("Registry MISS: threshold=%.2f", threshold)
    return MatchResult(hit=False, agent=None, similarity=0.0)
