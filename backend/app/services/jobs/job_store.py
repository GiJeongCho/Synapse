"""Job 상태 저장소 & 취소 확인(§17.3).

표준은 PostgreSQL 에 Job 상태를 적재하지만, 본 스캐폴드는 인메모리 구현을 제공한다.
운영 전환 시 본 모듈만 RDB(asyncpg) 구현으로 교체하면 호출부는 영향이 없다.
"""

from __future__ import annotations

from typing import Dict

from app.core.enums import JobStatus
from app.core.errors.exceptions import JobCancelledError
from app.core.logging import logger

log = logger(__name__)

_JOBS: Dict[str, JobStatus] = {}


def register_job(job_id: str) -> None:
    _JOBS[job_id] = JobStatus.RUNNING


def set_status(job_id: str, status: JobStatus) -> None:
    _JOBS[job_id] = status


def get_status(job_id: str) -> JobStatus | None:
    return _JOBS.get(job_id)


def request_cancel(job_id: str) -> bool:
    """취소 요청. Job 이 존재하면 CANCELED 로 표시하고 True 를 반환한다."""
    if job_id not in _JOBS:
        return False
    _JOBS[job_id] = JobStatus.CANCELED
    return True


async def check_if_canceled(job_id: str) -> None:
    """장기 작업의 분기점에서 호출한다(§17.3).

    상태가 CANCELED 면 ``JobCancelledError(AIJOB-006)`` 를 raise 한다.
    워커는 이를 정상 중단으로 처리(재-raise)한다.
    """
    if not job_id:
        return
    if _JOBS.get(job_id) == JobStatus.CANCELED:
        log.info("[Job | %s] 취소 감지 → 중단", job_id)
        raise JobCancelledError(details={"job_id": job_id})
