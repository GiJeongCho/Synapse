"""에이전트 실행 접수 라우터(§15.1)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.services.workers.research_worker import run_research_workflow

log = logger(__name__)

router = APIRouter()

_jobs: dict[str, dict[str, Any]] = {}


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, description="리서치 주제")
    instruction: str = Field("", description="추가 지시사항")


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None


async def _execute_research(job_id: str, topic: str, instruction: str):
    """백그라운드에서 리서치를 실행한다."""
    _jobs[job_id] = {"status": "running"}
    try:
        result = await run_research_workflow(topic, instruction, job_id)
        _jobs[job_id] = {"status": "completed", "result": result}
    except Exception as exc:
        log.error("Research 실행 실패: %s", exc, exc_info=True)
        _jobs[job_id] = {"status": "failed", "result": {"error": str(exc)}}


@router.post("/research", response_model=JobResponse)
async def execute_research(req: ResearchRequest, bg: BackgroundTasks):
    """리서치 워크플로우를 백그라운드로 실행한다."""
    import uuid

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending"}

    bg.add_task(_execute_research, job_id, req.topic, req.instruction)

    log.info("리서치 Job 접수: job_id=%s, topic=%s", job_id, req.topic[:60])
    return JobResponse(job_id=job_id, status="pending", message="리서치가 시작되었습니다.")


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Job 상태를 조회한다."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        result=job.get("result"),
    )
