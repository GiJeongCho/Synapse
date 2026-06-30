"""Meta-Agent 오케스트레이터 + 쌍방 Supervisor 그래프(§4).

create_meta_orchestrator():
    analyze → registry_lookup → [hit: END / miss_solo: solo / miss_dual: dual] → register → END

create_dual_supervisor_workflow():
    builder → critic → counter_review → [accept: consensus / challenge: critic]
    consensus → [agreed: END / next_round: builder / give_up: END]
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.agents.meta_agent.graph import create_meta_agent_workflow
from app.agents.meta_agent.nodes.requirements import requirements_analyzer
from app.agents.meta_supervisor.nodes.builder_supervisor import builder_supervisor
from app.agents.meta_supervisor.nodes.consensus import (
    consensus_check,
    route_consensus,
)
from app.agents.meta_supervisor.nodes.counter_review import (
    counter_review,
    route_after_counter,
)
from app.agents.meta_supervisor.nodes.critic_supervisor import critic_supervisor
from app.agents.meta_supervisor.nodes.registry_lookup import registry_lookup
from app.agents.meta_supervisor.state import DualSupervisorState
from app.core.config import settings
from app.core.logging import logger
from app.services.agent_registry import store as registry_store

log = logger(__name__)


# ──────────────────────────────────────────────────────────
# Solo 모드: 파이프라인 1회 실행 (Critic 없이)
# ──────────────────────────────────────────────────────────

async def _solo_pipeline(
    state: DualSupervisorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """파이프라인 1회 실행 → 즉시 배포 (Solo 모드)."""
    log.info("Solo 모드 파이프라인 실행")

    pipeline = create_meta_agent_workflow()
    result = await pipeline.ainvoke(
        {
            "job_id": state.get("job_id", ""),
            "user_request": state["user_request"],
            "retry_count": 0,
        },
        config=config,
    )

    current_result = {
        "agent_spec": result.get("agent_spec", {}),
        "system_prompt": result.get("system_prompt", ""),
        "project_files": result.get("project_files", {}),
        "mcp_tools": result.get("mcp_tools", []),
        "test_result": result.get("test_result", {}),
    }

    return {
        "current_result": current_result,
        "best_result": current_result,
        "agent_spec": result.get("agent_spec", {}),
    }


# ──────────────────────────────────────────────────────────
# Registry 등록 노드
# ──────────────────────────────────────────────────────────

def _graph_from_project_files(project_files: dict[str, Any]) -> dict[str, Any]:
    """project_files의 workflow/tools로 React Flow 그래프를 만든다 (Solo 폴백)."""
    pf = project_files if isinstance(project_files, dict) else {}
    steps = pf.get("workflow") or [
        t.get("tool_id", "").split("__", 1)[-1]
        for t in pf.get("tools", []) if isinstance(t, dict)
    ]
    names = [s if isinstance(s, str) else s.get("name", f"step_{i}")
             for i, s in enumerate(steps)] or ["agent"]

    nodes = [
        {
            "id": name,
            "type": "flowCard",
            "position": {"x": i * 240, "y": 0},
            "data": {"label": name, "desc": ""},
            "style": {"width": 180},
        }
        for i, name in enumerate(names)
    ]
    edges = [
        {
            "id": f"e-{names[i]}-{names[i + 1]}",
            "source": names[i],
            "target": names[i + 1],
            "animated": True,
        }
        for i in range(len(names) - 1)
    ]
    return {"nodes": nodes, "edges": edges}


async def _register_agent(
    state: DualSupervisorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """생성된 에이전트를 Registry에 등록한다."""
    result = state.get("best_result") or state.get("current_result") or {}
    if not result:
        log.warning("등록할 에이전트 결과가 없음")
        return {}

    agent_id = f"agent-{uuid.uuid4().hex[:12]}"
    mode = "dual" if state.get("critic_enabled", True) else "solo"

    record = {
        "agent_id": agent_id,
        "user_request": state["user_request"],
        "agent_spec": result.get("agent_spec", {}),
        "system_prompt": result.get("system_prompt", ""),
        "mcp_tools": result.get("mcp_tools", []),
        "project_files": result.get("project_files", {}),
        "test_result": result.get("test_result", {}),
        "graph_structure": result.get("graph_structure")
        or _graph_from_project_files(result.get("project_files", {})),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "mode": mode,
    }

    registry_store.register(record)
    log.info("Agent 등록 완료: %s (mode=%s)", agent_id, mode)

    return {
        "best_result": {**result, "agent_id": agent_id},
    }


# ──────────────────────────────────────────────────────────
# 라우팅 함수
# ──────────────────────────────────────────────────────────

def _route_after_lookup(state: DualSupervisorState) -> str:
    """Registry 조회 결과에 따라 라우팅한다."""
    if state.get("registry_hit"):
        return "hit"

    if state.get("critic_enabled", settings.meta_critic_enabled):
        return "miss_dual"

    return "miss_solo"


# ──────────────────────────────────────────────────────────
# 쌍방 Supervisor 워크플로우 (Dual 모드)
# ──────────────────────────────────────────────────────────

def create_dual_supervisor_workflow():
    """쌍방 Supervisor 루프를 컴파일한다."""
    workflow = StateGraph(DualSupervisorState)

    workflow.add_node("builder", builder_supervisor)
    workflow.add_node("critic", critic_supervisor)
    workflow.add_node("counter_review", counter_review)
    workflow.add_node("consensus_check", consensus_check)

    workflow.set_entry_point("builder")
    workflow.add_edge("builder", "critic")
    workflow.add_edge("critic", "counter_review")
    workflow.add_conditional_edges("counter_review", route_after_counter, {
        "accept": "consensus_check",
        "challenge": "critic",
    })
    workflow.add_conditional_edges("consensus_check", route_consensus, {
        "agreed": END,
        "next_round": "builder",
        "give_up": END,
    })

    return workflow.compile()


# ──────────────────────────────────────────────────────────
# 최상위 오케스트레이터
# ──────────────────────────────────────────────────────────

def create_meta_orchestrator():
    """최상위 워크플로우: Registry 조회 + 모드 분기 + 배포."""
    workflow = StateGraph(DualSupervisorState)

    workflow.add_node("analyze", requirements_analyzer)
    workflow.add_node("registry_lookup", registry_lookup)
    workflow.add_node("solo_pipeline", _solo_pipeline)
    workflow.add_node("dual_loop", create_dual_supervisor_workflow())
    workflow.add_node("register", _register_agent)

    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "registry_lookup")
    workflow.add_conditional_edges("registry_lookup", _route_after_lookup, {
        "hit": END,
        "miss_solo": "solo_pipeline",
        "miss_dual": "dual_loop",
    })
    workflow.add_edge("solo_pipeline", "register")
    workflow.add_edge("dual_loop", "register")
    workflow.add_edge("register", END)

    return workflow.compile()
