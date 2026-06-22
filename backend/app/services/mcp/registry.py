"""MCP Registry — 고수준 MCP 도구 검색 인터페이스.

에이전트 명세(agent_spec)에서 필요한 능력(capabilities)을 추출하고
MCP Schema Store에서 매칭되는 도구를 찾는다.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import logger
from app.services.mcp import schema_store

log = logger(__name__)


def find_tools_for_spec(
    agent_spec: dict[str, Any],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """에이전트 명세를 기반으로 필요한 MCP 도구를 검색한다.

    agent_spec에서 required_capabilities, goal, persona 등을 조합하여
    자연어 검색 쿼리를 생성하고 Schema Store에서 유사도 검색한다.

    Returns:
        매칭된 MCP 도구 목록 (score 내림차순).
    """
    capabilities = agent_spec.get("required_capabilities", [])
    goal = agent_spec.get("goal", "")

    query_parts = []
    if goal:
        query_parts.append(goal)
    if capabilities:
        query_parts.append("capabilities: " + ", ".join(capabilities))

    query = ". ".join(query_parts) if query_parts else str(agent_spec)

    tools = schema_store.search_tools(query, top_k=top_k)
    log.info("MCP 도구 검색: query=%s → %d개 매칭", query[:80], len(tools))
    return tools
