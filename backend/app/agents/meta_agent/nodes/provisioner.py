"""Provisioner 노드(§6) — 실행 가능한 MCP 도구 Python 코드를 생성하고 저장한다."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.prompts import PROVISIONER_PROMPT
from app.agents.meta_agent.state import MetaAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger
from app.services.mcp.tool_runtime import save_tool

log = logger(__name__)


async def provisioner(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """agent_spec + mcp_tools → system_prompt + 실행 가능한 도구 파일 생성."""
    agent_spec = state["agent_spec"]
    mcp_tools = state.get("mcp_tools", [])
    feedback = state.get("test_result", {}).get("suggestions", [])

    log.info("Provisioner 시작: %s", agent_spec.get("persona", "?")[:40])

    llm = get_llm_for_agent("meta")

    feedback_str = json.dumps(feedback, ensure_ascii=False) if feedback else "None"
    tools_summary = json.dumps(
        [{"name": t.get("name"), "capabilities": t.get("capabilities")} for t in mcp_tools[:5]],
        ensure_ascii=False,
    )

    messages = PROVISIONER_PROMPT.format_messages(
        agent_spec=json.dumps(agent_spec, ensure_ascii=False, indent=2),
        mcp_tools=tools_summary,
        feedback=feedback_str,
    )
    response = await llm.ainvoke(messages)
    result = extract_json_from_llm_response(response.content)

    system_prompt = result.get("system_prompt", "")
    agent_id = result.get("agent_id", "agent_" + state.get("job_id", "unknown")[:8])
    tools = result.get("tools", [])
    workflow = result.get("workflow", [])

    saved_tools = []
    for tool in tools:
        tool_id = tool.get("tool_id", "")
        code = tool.get("code", "")
        if not tool_id or not code:
            continue

        full_tool_id = f"{agent_id}__{tool_id}"
        save_tool(full_tool_id, code, metadata={
            "agent_id": agent_id,
            "name": tool.get("name", tool_id),
            "description": tool.get("description", ""),
            "functions": tool.get("functions", [tool_id]),
        })
        saved_tools.append({
            "tool_id": full_tool_id,
            "name": tool.get("name", tool_id),
            "functions": tool.get("functions", [tool_id]),
        })

    required_env = result.get("required_env", [])

    project_files = {
        "tools": saved_tools,
        "workflow": workflow,
        "agent_id": agent_id,
        "required_env": required_env,
    }

    log.info(
        "Provisioner 완료: agent_id=%s, %d개 도구 저장",
        agent_id, len(saved_tools),
    )

    return {
        "system_prompt": system_prompt,
        "project_files": project_files,
        "current_step": "provisioner",
    }
