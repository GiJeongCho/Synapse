"""생성된 MCP 도구 관리/실행 API."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.services.mcp.tool_runtime import execute_tool, list_tools, save_tool

log = logger(__name__)

router = APIRouter()


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
