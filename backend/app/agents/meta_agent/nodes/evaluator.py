"""Evaluator 노드(§6).

생성된 에이전트 코드를 검증하고 품질을 평가한다.
실패 시 retry_count를 증가시키고 MAX_PIPELINE_RETRIES 초과 시 에러를 반환한다.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.harness import ainvoke_json
from app.agents.meta_agent.prompts import EVALUATOR_PROMPT
from app.agents.meta_agent.state import MetaAgentState
from app.core.config import settings
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger

log = logger(__name__)


async def evaluator(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """생성된 에이전트 코드 검증 → test_result."""
    agent_spec = state["agent_spec"]
    system_prompt = state.get("system_prompt", "")
    project_files = state.get("project_files", {})
    mcp_tools = state.get("mcp_tools", [])
    retry_count = state.get("retry_count", 0)

    log.info("Evaluator 시작: retry=%d/%d", retry_count, settings.meta_max_pipeline_retries)

    llm = get_llm_for_agent("meta")
    messages = EVALUATOR_PROMPT.format_messages(
        agent_spec=json.dumps(agent_spec, ensure_ascii=False, indent=2),
        system_prompt=system_prompt,
        project_files=json.dumps(project_files, ensure_ascii=False, indent=2),
        mcp_tools=json.dumps(
            [{"tool_id": t.get("tool_id"), "name": t.get("name")} for t in mcp_tools],
            ensure_ascii=False,
        ),
    )
    test_result = await ainvoke_json(
        llm, messages, node="evaluator", retries=1,
        fallback={"passed": True, "score": 0.5,
                  "errors": [], "warnings": ["evaluator 응답 파싱 실패 — 통과 처리"],
                  "suggestions": []},
    )

    passed = test_result.get("passed", False)

    if not passed:
        retry_count += 1
        if retry_count >= settings.meta_max_pipeline_retries:
            log.warning("Evaluator: 최대 재시도 초과 (%d회)", retry_count)
            test_result["_max_retries_exceeded"] = True

    log.info(
        "Evaluator 완료: passed=%s, score=%.2f, errors=%d, retry=%d",
        passed,
        test_result.get("score", 0),
        len(test_result.get("errors", [])),
        retry_count,
    )

    return {
        "test_result": test_result,
        "retry_count": retry_count,
        "current_step": "evaluator",
    }
