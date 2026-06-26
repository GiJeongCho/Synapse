"""스케줄 관리 API — 에이전트 자동 실행 스케줄 등록/해제/조회."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.services.scheduler.engine import (
    get_schedule_logs,
    list_schedules,
    register_schedule,
    remove_schedule,
)

log = logger(__name__)

router = APIRouter()


class RegisterScheduleRequest(BaseModel):
    agent_id: str = Field(..., description="에이전트 ID")
    cron: str = Field(..., description="cron 표현식 (분 시 일 월 요일)")
    description: str = Field(default="", description="스케줄 설명")


class ScheduleResponse(BaseModel):
    schedule_id: str
    agent_id: str
    cron: str
    description: str
    enabled: bool
    next_run: Optional[str] = None
    active: Optional[bool] = None


@router.post("/register", response_model=ScheduleResponse)
async def api_register_schedule(req: RegisterScheduleRequest):
    """에이전트에 대한 스케줄을 등록한다.

    agent_id에 해당하는 MCP 도구를 자동으로 찾아 스케줄에 연결한다.
    """
    from app.services.mcp.tool_runtime import resolve_agent_tools
    from app.services.agent_registry import store as registry_store

    record = registry_store.get(req.agent_id)
    project_files = record.get("project_files") if record else None
    agent_tools = resolve_agent_tools(req.agent_id, project_files)

    if not agent_tools:
        raise HTTPException(
            status_code=404,
            detail=f"에이전트 '{req.agent_id}'에 연결된 도구가 없습니다.",
        )

    tool_refs = [
        {"tool_id": t["tool_id"], "functions": t.get("functions", [])}
        for t in agent_tools
    ]

    try:
        result = register_schedule(
            agent_id=req.agent_id,
            cron_expression=req.cron,
            tools=tool_refs,
            description=req.description,
        )
        return ScheduleResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("스케줄 등록 실패: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{schedule_id}")
async def api_remove_schedule(schedule_id: str):
    """스케줄을 해제한다."""
    removed = remove_schedule(schedule_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"스케줄을 찾을 수 없습니다: {schedule_id}")
    return {"status": "removed", "schedule_id": schedule_id}


@router.get("/list")
async def api_list_schedules():
    """등록된 모든 스케줄 목록을 반환한다."""
    schedules = list_schedules()
    return {"schedules": schedules, "total": len(schedules)}


@router.get("/{schedule_id}/logs")
async def api_get_logs(schedule_id: str, limit: int = 20):
    """특정 스케줄의 실행 로그를 반환한다."""
    logs = get_schedule_logs(schedule_id, limit=limit)
    return {"schedule_id": schedule_id, "logs": logs, "total": len(logs)}


@router.post("/{schedule_id}/run-now")
async def api_run_now(schedule_id: str):
    """스케줄을 즉시 1회 실행한다 (테스트용)."""
    from app.services.scheduler.engine import _run_agent_tools

    schedules = list_schedules()
    target = next((s for s in schedules if s["schedule_id"] == schedule_id), None)

    if not target:
        raise HTTPException(status_code=404, detail=f"스케줄을 찾을 수 없습니다: {schedule_id}")

    try:
        await _run_agent_tools(
            schedule_id=schedule_id,
            agent_id=target["agent_id"],
            tools=target["tools"],
        )
        return {"status": "executed", "schedule_id": schedule_id}
    except Exception as exc:
        log.error("즉시 실행 실패: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
