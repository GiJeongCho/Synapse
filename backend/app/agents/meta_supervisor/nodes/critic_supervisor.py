"""Critic Supervisor 노드(§6) — Supervisor-B (토글 가능).

Builder의 결과를 평가하고 개선안을 제시한다.
critic_enabled=false이면 이 노드는 실행되지 않는다(graph 레벨에서 스킵).
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_supervisor.prompts import CRITIC_PROMPT
from app.agents.meta_supervisor.state import DualSupervisorState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)

_DEFAULT_CRITERIA = {
    "functionality": {"weight": 0.3, "min_score": 0.6},
    "tool_integration": {"weight": 0.25, "min_score": 0.5},
    "prompt_quality": {"weight": 0.2, "min_score": 0.5},
    "code_quality": {"weight": 0.15, "min_score": 0.4},
    "completeness": {"weight": 0.1, "min_score": 0.5},
}


async def critic_supervisor(
    state: DualSupervisorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Builder 결과 평가 → evaluation + improvement_plan."""
    current_round = state.get("round", 0)
    eval_criteria = state.get("eval_criteria") or _DEFAULT_CRITERIA

    log.info("Critic 평가 시작: round=%d", current_round)

    llm = get_llm_for_agent("meta_critic")
    messages = CRITIC_PROMPT.format_messages(
        user_request=state["user_request"],
        round=current_round,
        builder_strategy=json.dumps(state.get("builder_strategy") or {}, ensure_ascii=False),
        current_result=json.dumps(state.get("current_result") or {}, ensure_ascii=False, indent=2),
        eval_criteria=json.dumps(eval_criteria, ensure_ascii=False),
        history=json.dumps(state.get("history", [])[-3:], ensure_ascii=False),
    )
    response = await llm.ainvoke(messages)
    evaluation = extract_json_from_llm_response(response.content)

    criteria_updates = evaluation.pop("eval_criteria_updates", None)
    if criteria_updates:
        eval_criteria = {**eval_criteria, **criteria_updates}

    improvement_plan = evaluation.get("improvement_plan", [])

    log.info(
        "Critic 완료: passed=%s, overall=%.2f, errors=%d",
        evaluation.get("passed", False),
        evaluation.get("overall_score", 0),
        len(evaluation.get("errors", [])),
    )

    if evaluation.get("passed") and not evaluation.get("errors"):
        best_result = state.get("current_result")
    else:
        best_result = state.get("best_result")

    return {
        "evaluation": evaluation,
        "improvement_plan": {"suggestions": improvement_plan},
        "eval_criteria": eval_criteria,
        "best_result": best_result or state.get("current_result"),
        "history": [{
            "round": current_round,
            "role": "critic",
            "passed": evaluation.get("passed", False),
            "overall_score": evaluation.get("overall_score", 0),
        }],
    }
