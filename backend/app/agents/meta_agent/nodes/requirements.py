"""Requirements Analyzer 노드(§6).

사용자의 자연어 요구사항을 분석하여 에이전트 명세(agent_spec)를 생성한다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.harness import ainvoke_json
from app.agents.meta_agent.prompts import REQUIREMENTS_PROMPT
from app.agents.meta_agent.state import MetaAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger

log = logger(__name__)


async def requirements_analyzer(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """사용자 요구사항 → 에이전트 명세 JSON."""
    user_request = state["user_request"]
    log.info("Requirements 분석 시작: %s", user_request[:80])

    llm = get_llm_for_agent("meta")
    messages = REQUIREMENTS_PROMPT.format_messages(user_request=user_request)

    agent_spec = await ainvoke_json(
        llm, messages, node="requirements", retries=2,
        fallback={"persona": "General Agent", "goal": user_request[:200],
                  "constraints": [], "required_capabilities": [],
                  "input_format": "text", "output_format": "text"},
    )
    log.info(
        "Requirements 완료: persona=%s, capabilities=%s",
        agent_spec.get("persona", "?")[:40],
        agent_spec.get("required_capabilities", []),
    )

    return {
        "agent_spec": agent_spec,
        "current_step": "requirements",
    }
