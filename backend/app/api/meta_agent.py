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
                "agent_id": r.get("agent_id", r.get("id", "")),
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


@router.get("/registry/{agent_id}")
async def get_agent_detail(agent_id: str):
    """특정 에이전트의 상세 정보를 반환한다."""
    try:
        registry_store.ensure_collection()
        from app.vectordb.milvus_client import get_client
        client = get_client()
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
