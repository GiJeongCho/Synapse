"""Job 취소/상태 라우터(§15.1, §17.3)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.enums import JobStatus
from app.services.jobs import get_status, request_cancel

router = APIRouter()


@router.get("/{job_id}")
async def job_status(job_id: str):
    """Job 의 현재 상태를 조회한다."""
    status = get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job ID 없음")
    return {"job_id": job_id, "status": status.value}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Job 취소를 요청한다. 워커는 다음 분기점에서 정상 중단한다."""
    ok = request_cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job ID 없음")
    return {"job_id": job_id, "status": JobStatus.CANCELED.value}
