"""생성된 MCP 도구 관리/실행 API."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.services.mcp.tool_runtime import (
    dedupe_generated_tools,
    execute_tool,
    list_tools,
    remove_orphan_tools,
    save_tool,
)

log = logger(__name__)

router = APIRouter()


def _known_agent_prefixes() -> set[str]:
    """레지스트리에 등록된 에이전트의 식별자/도구 접두사를 모두 수집한다."""
    import json as _json

    from app.core.config import settings
    from app.services.agent_registry import store as registry_store
    from app.vectordb.milvus_client import get_client

    known: set[str] = set()
    registry_store.ensure_collection()
    client = get_client()
    rows = client.query(
        collection_name=settings.meta_registry_collection,
        filter="",
        output_fields=["agent_id", "project_files"],
        limit=1000,
    )
    for r in rows:
        for key in ("id", "agent_id"):
            v = r.get(key)
            if v:
                known.add(str(v))
        pf = r.get("project_files")
        if isinstance(pf, str):
            try:
                pf = _json.loads(pf)
            except (ValueError, TypeError):
                pf = None
        if isinstance(pf, dict):
            if pf.get("agent_id"):
                known.add(str(pf["agent_id"]))
            for t in pf.get("tools", []):
                tid = t.get("tool_id") if isinstance(t, dict) else None
                if tid:
                    known.add(str(tid).split("__", 1)[0])
    return known


@router.post("/cleanup")
async def cleanup_tools(remove_orphans: bool = True):
    """중복 도구를 정리한다.

    - remove_orphans=True: 레지스트리에 없는(삭제된) 에이전트의 잔여 도구 그룹 삭제
    - 항상: 에이전트별 단계당 1개만 남기고 중복 도구 삭제
    """
    orphan_report: dict[str, Any] = {"deleted": [], "kept_groups": []}
    if remove_orphans:
        try:
            known = _known_agent_prefixes()
            orphan_report = remove_orphan_tools(known)
        except Exception as exc:  # noqa: BLE001 — 레지스트리 조회 실패해도 dedup 은 진행
            log.warning("고아 도구 정리 건너뜀(레지스트리 조회 실패): %s", exc)
            orphan_report["error"] = str(exc)

    dedup_report = dedupe_generated_tools()

    return {
        "status": "ok",
        "orphans_removed": len(orphan_report.get("deleted", [])),
        "duplicates_removed": len(dedup_report.get("deleted", [])),
        "orphan_detail": orphan_report,
        "dedup_detail": dedup_report,
    }


class ToolListResponse(BaseModel):
    tools: list[dict[str, Any]]
    total: int


class ExecuteToolRequest(BaseModel):
    function_name: str = Field(..., description="실행할 함수 이름")
    arguments: dict[str, Any] = Field(default_factory=dict, description="함수 인자")
    timeout: float = Field(default=60.0, ge=5, le=300, description="타임아웃(초)")


class ExecuteToolResponse(BaseModel):
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@router.get("/list", response_model=ToolListResponse)
async def get_tool_list():
    """저장된 모든 MCP 도구 목록을 반환한다."""
    tools = list_tools()
    return ToolListResponse(tools=tools, total=len(tools))


@router.get("/{tool_id}")
async def get_tool_detail(tool_id: str):
    """특정 도구의 상세 정보 (코드 포함)를 반환한다."""
    from pathlib import Path
    from app.core.config import settings
    import json

    tools_dir = Path(settings.upload_dir).parent / "generated_tools" / tool_id
    tool_path = tools_dir / "tool.py"
    meta_path = tools_dir / "metadata.json"

    if not tool_path.exists():
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")

    code = tool_path.read_text(encoding="utf-8")
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    return {
        "tool_id": tool_id,
        "code": code,
        **meta,
    }


@router.post("/{tool_id}/execute", response_model=ExecuteToolResponse)
async def run_tool(tool_id: str, req: ExecuteToolRequest):
    """특정 MCP 도구의 함수를 실행한다."""
    log.info("도구 실행 요청: %s/%s", tool_id, req.function_name)

    result = await execute_tool(
        tool_id=tool_id,
        function_name=req.function_name,
        arguments=req.arguments,
        timeout=req.timeout,
    )

    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail=result.get("error", "Tool not found"))

    return ExecuteToolResponse(
        status=result["status"],
        result=result.get("result"),
        error=result.get("error") or result.get("stderr"),
    )
