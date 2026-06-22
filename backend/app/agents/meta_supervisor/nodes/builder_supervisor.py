"""Builder Supervisor 노드(§6) — Supervisor-A.

전략을 수립하고 에이전트 생성 파이프라인을 실행한다.
이전 라운드의 Critic 피드백을 반영하여 전략을 조정한다.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.graph import create_meta_agent_workflow
from app.agents.meta_supervisor.prompts import BUILDER_PROMPT
from app.agents.meta_supervisor.state import DualSupervisorState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def builder_supervisor(
    state: DualSupervisorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """전략 수립 + 파이프라인 실행."""
    current_round = state.get("round", 0)
    user_request = state["user_request"]

    log.info("Builder 시작: round=%d", current_round)

    llm = get_llm_for_agent("meta_builder")
    messages = BUILDER_PROMPT.format_messages(
        user_request=user_request,
        round=current_round,
        evaluation=json.dumps(state.get("evaluation") or {}, ensure_ascii=False),
        improvement_plan=json.dumps(state.get("improvement_plan") or {}, ensure_ascii=False),
        prev_strategy=json.dumps(state.get("builder_strategy") or {}, ensure_ascii=False),
        history=json.dumps(state.get("history", [])[-3:], ensure_ascii=False),
    )
    response = await llm.ainvoke(messages)
    strategy = extract_json_from_llm_response(response.content)

    log.info("Builder 전략 수립: confidence=%.2f", strategy.get("confidence", 0))

    pipeline = create_meta_agent_workflow()
    pipeline_result = await pipeline.ainvoke(
        {
            "job_id": state.get("job_id", ""),
            "user_request": user_request,
            "retry_count": 0,
        },
        config=config,
    )

    current_result = {
        "agent_spec": pipeline_result.get("agent_spec", {}),
        "system_prompt": pipeline_result.get("system_prompt", ""),
        "project_files": pipeline_result.get("project_files", {}),
        "mcp_tools": pipeline_result.get("mcp_tools", []),
        "test_result": pipeline_result.get("test_result", {}),
    }

    log.info(
        "Builder 완료: round=%d, test_passed=%s",
        current_round,
        pipeline_result.get("test_result", {}).get("passed", False),
    )

    return {
        "current_result": current_result,
        "builder_strategy": strategy,
        "agent_spec": pipeline_result.get("agent_spec", {}),
        "round": current_round + 1,
        "history": [{
            "round": current_round,
            "role": "builder",
            "strategy": strategy,
            "test_passed": pipeline_result.get("test_result", {}).get("passed", False),
        }],
    }
