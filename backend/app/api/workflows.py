"""워크플로우 그래프 API — 내장 + 동적 생성 에이전트의 그래프 구조를 제공한다."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.logging import logger
from app.services.graph_serializer import (
    BUILTIN_WORKFLOW_NAMES,
    get_builtin_workflow_graph,
)

log = logger(__name__)

router = APIRouter()


@router.get("/builtin")
async def list_builtin_workflows() -> list[dict[str, str]]:
    """내장 워크플로우 목록을 반환한다."""
    from app.services.graph_serializer import _DISPLAY_NAMES, _CATEGORIES

    return [
        {
            "name": name,
            "display_name": _DISPLAY_NAMES.get(name, name),
            "category": _CATEGORIES.get(name, "기타"),
        }
        for name in BUILTIN_WORKFLOW_NAMES
    ]


@router.get("/builtin/{workflow_name}")
async def get_builtin_workflow(workflow_name: str) -> dict[str, Any]:
    """내장 워크플로우의 React Flow 그래프 구조를 반환한다."""
    if workflow_name not in BUILTIN_WORKFLOW_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown workflow: {workflow_name}. Available: {BUILTIN_WORKFLOW_NAMES}",
        )

    result = get_builtin_workflow_graph(workflow_name)
    if result is None:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract graph for: {workflow_name}",
        )

    return result


@router.get("/agent/{agent_id}")
async def get_agent_workflow(agent_id: str) -> dict[str, Any]:
    """Meta-Agent로 생성된 에이전트의 저장된 그래프 구조를 반환한다."""
    from app.services.agent_registry import store as registry_store
    try:
        record = registry_store.get(agent_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        graph_json = record.get("graph_structure")
        if not graph_json:
            raise HTTPException(
                status_code=404,
                detail=f"No graph structure stored for agent: {agent_id}",
            )
        
        import json

        if isinstance(graph_json, str):
            graph_data = json.loads(graph_json)
        else:
            graph_data = graph_json

        if not isinstance(graph_data, dict) or not graph_data.get("nodes"):
            raise HTTPException(
                status_code=404,
                detail=f"No graph structure stored for agent: {agent_id}",
            )

        graph_data.setdefault("nodes", [])
        graph_data.setdefault("edges", [])
        graph_data["agent_id"] = agent_id
        graph_data["display_name"] = record.get("user_request", agent_id)[:50]
        graph_data["category"] = "생성된 에이전트"
        return graph_data

    except HTTPException:
        raise
    except Exception as exc:
        log.error("에이전트 그래프 조회 실패: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
