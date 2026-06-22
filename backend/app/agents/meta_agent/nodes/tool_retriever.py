"""Tool & Context Retriever 노드(§6).

에이전트 명세에서 필요한 MCP 도구를 검색한다.
LLM 호출 없이 MCP Registry(Vector DB)에서 유사도 검색만 수행한다.
"""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.state import MetaAgentState
from app.core.logging import logger
from app.services.mcp.registry import find_tools_for_spec

log = logger(__name__)


async def tool_retriever(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """agent_spec → MCP 도구 목록 검색."""
    agent_spec = state["agent_spec"]
    log.info("Tool Retriever 시작: capabilities=%s", agent_spec.get("required_capabilities", []))

    matched_tools = find_tools_for_spec(agent_spec, top_k=5)

    tools_summary = [
        {"tool_id": t["tool_id"], "name": t.get("name", ""), "uri": t.get("uri", ""), "score": t.get("score", 0)}
        for t in matched_tools
    ]

    log.info("Tool Retriever 완료: %d개 도구 매칭", len(tools_summary))

    return {
        "mcp_tools": matched_tools,
        "current_step": "tool_retriever",
    }
