"""Environment Provisioner 노드(§6).

에이전트 명세 + MCP 도구 목록을 받아 실행 가능한 에이전트 코드를 생성한다.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.prompts import PROVISIONER_PROMPT
from app.agents.meta_agent.state import MetaAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)


async def provisioner(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """agent_spec + mcp_tools → system_prompt + project_files."""
    agent_spec = state["agent_spec"]
    mcp_tools = state.get("mcp_tools", [])
    feedback = state.get("test_result", {}).get("suggestions", [])

    log.info("Provisioner 시작: %s", agent_spec.get("persona", "?")[:40])

    llm = get_llm_for_agent("meta")

    feedback_str = json.dumps(feedback, ensure_ascii=False) if feedback else "None"

    messages = PROVISIONER_PROMPT.format_messages(
        agent_spec=json.dumps(agent_spec, ensure_ascii=False, indent=2),
        mcp_tools=json.dumps(mcp_tools, ensure_ascii=False, indent=2),
        feedback=feedback_str,
    )
    response = await llm.ainvoke(messages)
    result = extract_json_from_llm_response(response.content)

    system_prompt = result.get("system_prompt", "")
    project_files = result.get("project_files", {})

    log.info(
        "Provisioner 완료: %d개 파일 생성, prompt 길이=%d",
        len(project_files),
        len(system_prompt),
    )

    return {
        "system_prompt": system_prompt,
        "project_files": project_files,
        "current_step": "provisioner",
    }
