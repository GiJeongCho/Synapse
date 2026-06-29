"""Meta-Agent API 엔드포인트.

에이전트 생성 요청과 Registry 조회 기능을 제공한다.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.meta_supervisor.graph import create_meta_orchestrator
from app.core.config import settings
from app.core.logging import logger
from app.services.agent_registry import store as registry_store
from app.vectordb.milvus_client import embed_texts

log = logger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────────────────
# 요청/응답 스키마
# ──────────────────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    user_request: str = Field(..., min_length=5, description="에이전트 생성 요구사항")
    critic_enabled: Optional[bool] = Field(None, description="Critic on/off (None이면 설정값 사용)")
    max_rounds: Optional[int] = Field(None, ge=1, le=10, description="최대 라운드 수")


class CreateAgentResponse(BaseModel):
    agent_id: str
    mode: str
    registry_hit: bool
    result: dict[str, Any]


class RegistryListResponse(BaseModel):
    agents: list[dict[str, Any]]
    total: int


# ──────────────────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────────────────

@router.post("/create", response_model=CreateAgentResponse)
async def create_agent(req: CreateAgentRequest):
    """에이전트 생성 요청을 처리한다.

    1. Registry 조회로 기존 에이전트 재사용 가능 여부 확인
    2. Solo/Dual 모드에 따라 파이프라인 실행
    3. 결과를 Registry에 등록하고 반환
    """
    log.info("에이전트 생성 요청: %s", req.user_request[:80])

    critic_enabled = req.critic_enabled if req.critic_enabled is not None else settings.meta_critic_enabled
    max_rounds = req.max_rounds or settings.meta_max_rounds

    try:
        orchestrator = create_meta_orchestrator()
        result = await orchestrator.ainvoke({
            "job_id": "",
            "user_request": req.user_request,
            "critic_enabled": critic_enabled,
            "max_rounds": max_rounds,
            "round": 0,
            "history": [],
            "stale_count": 0,
            "is_agreed": False,
        })
    except Exception as exc:
        log.error("에이전트 생성 실패: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    registry_hit = result.get("registry_hit", False)

    if registry_hit:
        matched = result.get("registry_match", {})
        return CreateAgentResponse(
            agent_id=matched.get("agent_id", "unknown"),
            mode="reuse",
            registry_hit=True,
            result=matched,
        )

    best = result.get("best_result") or result.get("current_result") or {}
    mode = "dual" if critic_enabled else "solo"

    return CreateAgentResponse(
        agent_id=best.get("agent_id", "unknown"),
        mode=mode,
        registry_hit=False,
        result=best,
    )


@router.get("/registry", response_model=RegistryListResponse)
async def list_registry():
    """등록된 에이전트 목록을 반환한다."""
    try:
        registry_store.ensure_collection()
        from app.vectordb.milvus_client import get_client
        client = get_client()
        results = client.query(
            collection_name=settings.meta_registry_collection,
            filter="",
            output_fields=["agent_id", "user_request", "mode", "version", "created_at"],
            limit=100,
        )
        agents = [
            {
                "agent_id": r.get("id", r.get("agent_id", "")),
                "user_request": r.get("user_request", ""),
                "mode": r.get("mode", ""),
                "version": r.get("version", 1),
                "created_at": r.get("created_at", ""),
            }
            for r in results
        ]
        return RegistryListResponse(agents=agents, total=len(agents))
    except Exception as exc:
        log.error("Registry 조회 실패: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/registry/{agent_id}")
async def delete_agent(agent_id: str):
    """에이전트를 Registry에서 삭제한다.

    연관된 MCP 도구도 함께 정리하되, 도구 청소부(심판) 에이전트가
    공용/필수/타 에이전트 사용 도구를 보호하고 전용 도구만 삭제한다.
    """
    from app.services.mcp.tool_janitor import judge_tool_deletions
    from app.services.mcp.tool_runtime import (
        delete_tool,
        delete_tools_for_agent,
        list_tools,
        resolve_agent_tools,
    )

    try:
        registry_store.ensure_collection()
        from app.vectordb.milvus_client import get_client
        client = get_client()

        results = client.query(
            collection_name=settings.meta_registry_collection,
            filter=f'id == "{agent_id}"',
            output_fields=["agent_id", "project_files"],
            limit=1,
        )
        stored_agent_id = results[0].get("agent_id", agent_id) if results else agent_id

        # 실제 도구 폴더는 provisioner의 snake_case agent_id로 prefix되므로
        # project_files를 이용해 정확히 찾아 삭제한다.
        project_files = None
        if results:
            pf_raw = results[0].get("project_files")
            if isinstance(pf_raw, str):
                try:
                    import json as _json
                    project_files = _json.loads(pf_raw)
                except (ValueError, TypeError):
                    project_files = None
            elif isinstance(pf_raw, dict):
                project_files = pf_raw

        # 후보 도구 수집: project_files 매칭 + prefix 매칭(공용 도구 제외)
        candidates = list(resolve_agent_tools(agent_id, project_files))
        seen = {t["tool_id"] for t in candidates}
        for t in list_tools(include_shared=False):
            tid = t["tool_id"]
            if tid in seen:
                continue
            if tid.startswith(f"{stored_agent_id}__") or tid.startswith(f"{agent_id}__"):
                candidates.append(t)
                seen.add(tid)

        # 심판: 어떤 도구를 지울지 판단 (공용/필수/타 에이전트 도구는 보호)
        verdict = await judge_tool_deletions(agent_id, stored_agent_id, candidates)

        ok = registry_store.delete(agent_id)
        if not ok:
            raise HTTPException(status_code=500, detail="삭제 실패")

        protected_ids = {p["tool_id"] for p in verdict["protected"]}
        kept_ids = {k["tool_id"] for k in verdict["kept_by_judge"]}
        keep_set = protected_ids | kept_ids

        tools_deleted = 0
        for tid in verdict["delete"]:
            if delete_tool(tid):
                tools_deleted += 1
        # 보조 경로: prefix 매칭으로 누락분 정리(보호 도구는 제외)
        tools_deleted += delete_tools_for_agent(stored_agent_id, keep=keep_set)
        tools_deleted += delete_tools_for_agent(agent_id, keep=keep_set)

        log.info(
            "에이전트 삭제 완료: %s (도구 %d개 삭제, 보호 %d, 보존 %d)",
            agent_id, tools_deleted, len(protected_ids), len(kept_ids),
        )
        return {
            "status": "deleted",
            "agent_id": agent_id,
            "tools_deleted": tools_deleted,
            "protected_tools": verdict["protected"],
            "kept_tools": verdict["kept_by_judge"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.error("에이전트 삭제 실패: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/registry/{agent_id}")
async def get_agent_detail(agent_id: str):
    """특정 에이전트의 상세 정보를 반환한다."""
    try:
        registry_store.ensure_collection()
        from app.vectordb.milvus_client import get_client
        client = get_client()
        results = client.query(
            collection_name=settings.meta_registry_collection,
            filter=f'id == "{agent_id}"',
            output_fields=registry_store._FIELDS,
            limit=1,
        )
        if not results:
            results = client.query(
                collection_name=settings.meta_registry_collection,
                filter=f'agent_id == "{agent_id}"',
                output_fields=registry_store._FIELDS,
                limit=1,
            )
        if not results:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

        import json
        record = results[0]
        for field in ("agent_spec", "mcp_tools", "project_files", "test_result", "graph_structure"):
            val = record.get(field)
            if isinstance(val, str):
                try:
                    record[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass

        return record
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Agent 상세 조회 실패: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/registry/{agent_id}/prereqs")
async def check_agent_prereqs(agent_id: str):
    """에이전트 실행에 필요한 사전 요구사항을 점검한다."""
    from app.services.prereq_checker import check_prerequisites
    from app.services.mcp.tool_runtime import resolve_agent_tools

    try:
        detail = await get_agent_detail(agent_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    agent_spec = detail.get("agent_spec") if isinstance(detail, dict) else None
    user_request = detail.get("user_request", "") if isinstance(detail, dict) else ""
    project_files = detail.get("project_files") if isinstance(detail, dict) else None

    agent_tools = resolve_agent_tools(agent_id, project_files)

    checks = check_prerequisites(
        agent_spec=agent_spec if isinstance(agent_spec, dict) else None,
        tools=agent_tools,
        user_request=user_request,
    )

    all_ok = all(c["ok"] for c in checks) if checks else True

    return {
        "agent_id": agent_id,
        "all_ok": all_ok,
        "checks": checks,
        "tool_count": len(agent_tools),
    }


@router.post("/registry/{agent_id}/run")
async def run_agent(agent_id: str):
    """에이전트의 MCP 도구를 파이프라인으로 순차 실행한다.

    도구 간 결과를 자동으로 전달한다:
    fetch → summarize → email 같은 파이프라인이 연결됨.
    """
    from app.services.mcp.tool_runtime import resolve_agent_tools
    from app.services.prereq_checker import check_prerequisites
    from app.services.agent_runner import run_agent_pipeline

    try:
        detail = await get_agent_detail(agent_id)
    except HTTPException:
        raise

    agent_spec = detail.get("agent_spec") if isinstance(detail, dict) else None
    user_request = detail.get("user_request", "") if isinstance(detail, dict) else ""
    project_files = detail.get("project_files") if isinstance(detail, dict) else None

    agent_tools = resolve_agent_tools(agent_id, project_files)

    if not agent_tools:
        raise HTTPException(status_code=404, detail="실행할 도구가 없습니다.")

    checks = check_prerequisites(
        agent_spec=agent_spec if isinstance(agent_spec, dict) else None,
        tools=agent_tools,
        user_request=user_request,
    )
    failed_checks = [c for c in checks if not c["ok"]]
    if failed_checks:
        return {
            "status": "blocked",
            "message": "필수 설정이 누락되었습니다.",
            "failed_checks": failed_checks,
            "results": [],
        }

    result = await run_agent_pipeline(agent_id, agent_tools)
    return result
