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


def _build_graph_from_spec(agent_spec: dict[str, Any]) -> dict[str, Any]:
    """에이전트 스펙에서 React Flow 호환 그래프 구조를 생성한다."""
    nodes_spec = agent_spec.get("nodes", agent_spec.get("workflow", []))
    if isinstance(nodes_spec, list):
        node_names = [n if isinstance(n, str) else n.get("name", f"node_{i}") for i, n in enumerate(nodes_spec)]
    elif isinstance(nodes_spec, dict):
        node_names = list(nodes_spec.keys())
    else:
        node_names = ["agent"]

    if not node_names:
        node_names = ["agent"]

    x_gap = 240
    flow_nodes = []
    for i, name in enumerate(node_names):
        desc = ""
        if isinstance(nodes_spec, list) and i < len(nodes_spec) and isinstance(nodes_spec[i], dict):
            desc = nodes_spec[i].get("description", "")
        flow_nodes.append({
            "id": name,
            "type": "flowCard",
            "position": {"x": i * x_gap, "y": 0},
            "data": {"label": name, "desc": desc},
            "style": {"width": 180},
        })

    edge_defaults = {
        "animated": True,
        "style": {"stroke": "#5a6278", "strokeWidth": 2},
        "labelStyle": {"fill": "#c8cdd8", "fontSize": 11, "fontWeight": 600},
        "labelBgStyle": {"fill": "#1a1e2c", "stroke": "#3a3f52", "strokeWidth": 1},
        "labelBgPadding": [6, 4],
        "labelBgBorderRadius": 4,
    }

    flow_edges = []
    for i in range(len(node_names) - 1):
        flow_edges.append({
            **edge_defaults,
            "id": f"e-{node_names[i]}-{node_names[i + 1]}",
            "source": node_names[i],
            "target": node_names[i + 1],
        })

    return {"nodes": flow_nodes, "edges": flow_edges}


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

    project_files = pipeline_result.get("project_files", {})

    graph_spec = project_files if project_files.get("workflow") else pipeline_result.get("agent_spec", {})
    graph_structure = _build_graph_from_spec(graph_spec)

    current_result = {
        "agent_spec": pipeline_result.get("agent_spec", {}),
        "system_prompt": pipeline_result.get("system_prompt", ""),
        "project_files": project_files,
        "mcp_tools": pipeline_result.get("mcp_tools", []),
        "test_result": pipeline_result.get("test_result", {}),
        "graph_structure": graph_structure,
        "generated_tools": project_files.get("tools", []),
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
