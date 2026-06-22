"""Consensus 판정 노드(§6).

두 Supervisor의 합의 여부를 판정하고 라우팅한다.
- agreed: 합의 도달 → 배포
- next_round: 미합의 → 다음 라운드
- give_up: 상한 도달 → graceful 종료
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_supervisor.state import DualSupervisorState
from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)


async def consensus_check(
    state: DualSupervisorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """합의 여부를 판정한다."""
    current_round = state.get("round", 0)
    max_rounds = state.get("max_rounds", settings.meta_max_rounds)
    evaluation = state.get("evaluation") or {}
    counter = state.get("counter_review") or {}
    prev_stale = state.get("stale_count", 0)

    passed = evaluation.get("passed", False)
    accepted = counter.get("decision", "accept") == "accept"

    is_agreed = passed and accepted

    history = state.get("history", [])
    stale = _check_stale(history)
    stale_count = prev_stale + 1 if stale else 0

    log.info(
        "Consensus: round=%d/%d, passed=%s, accepted=%s, agreed=%s, stale=%d",
        current_round, max_rounds, passed, accepted, is_agreed, stale_count,
    )

    return {
        "is_agreed": is_agreed,
        "stale_count": stale_count,
    }


def _check_stale(history: list[dict]) -> bool:
    """직전 2라운드가 동일한 패턴(양측 무변경)인지 확인한다."""
    if len(history) < 4:
        return False

    recent = history[-4:]
    builder_entries = [h for h in recent if h.get("role") == "builder"]
    critic_entries = [h for h in recent if h.get("role") == "critic"]

    if len(builder_entries) < 2 or len(critic_entries) < 2:
        return False

    b1, b2 = builder_entries[-2], builder_entries[-1]
    c1, c2 = critic_entries[-2], critic_entries[-1]

    builder_same = (
        b1.get("test_passed") == b2.get("test_passed")
        and str(b1.get("strategy")) == str(b2.get("strategy"))
    )
    critic_same = (
        c1.get("passed") == c2.get("passed")
        and abs(c1.get("overall_score", 0) - c2.get("overall_score", 0)) < 0.05
    )

    return builder_same and critic_same


def route_consensus(state: DualSupervisorState) -> str:
    """합의 판정 결과에 따라 라우팅한다."""
    if state.get("is_agreed"):
        return "agreed"

    current_round = state.get("round", 0)
    max_rounds = state.get("max_rounds", settings.meta_max_rounds)
    stale_count = state.get("stale_count", 0)

    if current_round >= max_rounds:
        log.info("라운드 상한 도달: %d/%d", current_round, max_rounds)
        return "give_up"

    if stale_count >= 2:
        log.info("교착 감지: stale_count=%d", stale_count)
        return "give_up"

    return "next_round"
