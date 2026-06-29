"""Counter Review 노드(§6).

Builder가 Critic의 평가를 역평가한다.
수용(accept) 또는 이의(challenge)를 결정하고 라우팅한다.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.harness import ainvoke_json
from app.agents.meta_supervisor.prompts import COUNTER_REVIEW_PROMPT
from app.agents.meta_supervisor.state import DualSupervisorState
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger

log = logger(__name__)


async def counter_review(
    state: DualSupervisorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Critic의 평가를 역평가 → accept/challenge."""
    current_round = state.get("round", 0)

    log.info("Counter Review 시작: round=%d", current_round)

    llm = get_llm_for_agent("meta_builder")
    messages = COUNTER_REVIEW_PROMPT.format_messages(
        evaluation=json.dumps(state.get("evaluation") or {}, ensure_ascii=False),
        improvement_plan=json.dumps(state.get("improvement_plan") or {}, ensure_ascii=False),
        builder_strategy=json.dumps(state.get("builder_strategy") or {}, ensure_ascii=False),
        round=current_round,
        history=json.dumps(state.get("history", [])[-3:], ensure_ascii=False),
    )
    review = await ainvoke_json(
        llm, messages, node="counter_review", retries=1,
        fallback={"decision": "accept", "criteria_challenges": []},
    )

    decision = review.get("decision", "accept")

    log.info(
        "Counter Review 완료: decision=%s, challenges=%d",
        decision,
        len(review.get("criteria_challenges", [])),
    )

    return {
        "counter_review": review,
        "history": [{
            "round": current_round,
            "role": "counter_review",
            "decision": decision,
        }],
    }


def route_after_counter(state: DualSupervisorState) -> str:
    """Counter Review 결과에 따라 라우팅한다."""
    review = state.get("counter_review") or {}
    decision = review.get("decision", "accept")

    if decision == "challenge":
        return "challenge"
    return "accept"
