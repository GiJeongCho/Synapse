"""Planner 노드 — 빌드 전에 '어떻게 만들지'를 기획한다.

요청을 받으면 ① 도구(tool) vs 작은 에이전트(agent) 판단 ② todolist 작성
③ 구조(architecture) 설계를 수행한다. 이 계획은 Provisioner의 생성을 가이드한다.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.harness import ainvoke_json
from app.agents.meta_agent.prompts import PLANNER_PROMPT
from app.agents.meta_agent.state import MetaAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger

log = logger(__name__)


def _normalize_plan(plan: dict[str, Any], user_request: str) -> dict[str, Any]:
    """LLM이 일부 필드를 빠뜨려도 안전한 기본값으로 보정한다."""
    if not isinstance(plan, dict):
        plan = {}

    build_type = plan.get("build_type")
    if build_type not in ("tool", "agent"):
        build_type = "agent"

    architecture = plan.get("architecture")
    if not isinstance(architecture, dict):
        architecture = {"components": [], "data_flow": ""}
    architecture.setdefault("components", [])
    architecture.setdefault("data_flow", "")

    todolist = plan.get("todolist")
    if not isinstance(todolist, list) or not todolist:
        todolist = ["요청을 처리할 도구를 생성한다", "워크플로우를 연결한다"]

    return {
        "build_type": build_type,
        "rationale": plan.get("rationale", ""),
        "fetch_topic": str(plan.get("fetch_topic", "") or "").strip(),
        "architecture": architecture,
        "todolist": [str(t) for t in todolist],
    }


async def planner(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """user_request + agent_spec → build_type/todolist/architecture 계획."""
    user_request = state["user_request"]
    agent_spec = state.get("agent_spec", {})
    log.info("Planner 시작: %s", user_request[:80])

    llm = get_llm_for_agent("meta")
    messages = PLANNER_PROMPT.format_messages(
        user_request=user_request,
        agent_spec=json.dumps(agent_spec, ensure_ascii=False, indent=2),
    )

    raw = await ainvoke_json(llm, messages, node="planner", retries=1, fallback={})

    plan = _normalize_plan(raw, user_request)
    log.info(
        "Planner 완료: build_type=%s, 컴포넌트 %d개, todo %d개",
        plan["build_type"],
        len(plan["architecture"].get("components", [])),
        len(plan["todolist"]),
    )

    return {
        "plan": plan,
        "current_step": "planner",
    }
