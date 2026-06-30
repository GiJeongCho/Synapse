"""Registry Lookup 노드(§6).

Agent Registry에서 기존 에이전트를 유사도 검색한다.
HIT이면 기존 에이전트를 반환하고, MISS이면 생성 파이프라인으로 진행한다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_supervisor.state import DualSupervisorState
from app.core.logging import logger
from app.services.agent_registry.matcher import match_request

log = logger(__name__)


async def registry_lookup(
    state: DualSupervisorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Registry에서 기존 에이전트를 검색한다."""
    user_request = state["user_request"]
    log.info("Registry 조회 시작: %s", user_request[:80])

    result = match_request(user_request)

    log.info(
        "Registry 조회 완료: hit=%s, similarity=%.3f",
        result.hit,
        result.similarity,
    )

    return {
        "registry_hit": result.hit,
        "registry_match": result.agent,
        "registry_similarity": result.similarity,
    }
