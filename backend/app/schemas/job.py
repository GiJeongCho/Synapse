"""응답 스키마(§18.1).

접수 API 는 결과가 아니라 접수 확인(``JobResponse``)을 반환한다.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from app.core.enums import AIStepStatus, JobStatus


class Timing(BaseModel):
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    latency_ms: Optional[float] = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.RUNNING
    internal_step_status: AIStepStatus = AIStepStatus.REQUEST_RECEIVED
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    job_type: Optional[str] = None
    message: str = "작업이 대기열에 추가되었습니다."
    result: Optional[Any] = None
    metadata: Optional[dict] = None
    timing: Timing = Timing()
    error: Optional[dict] = None
