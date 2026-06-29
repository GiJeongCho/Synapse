"""Research 워크플로우 워커(§14) — 그래프 실행 및 결과 반환."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.logging import logger
from app.workflows.research.graph import create_research_workflow

log = logger(__name__)


async def run_research_workflow(
    topic: str,
    instruction: str = "",
    job_id: str | None = None,
) -> dict[str, Any]:
    """리서치 워크플로우를 실행하고 최종 결과를 반환한다."""
    job_id = job_id or str(uuid.uuid4())

    log.info("리서치 워크플로우 시작: job_id=%s, topic=%s", job_id, topic[:60])

    try:
        workflow = create_research_workflow()
        result = await workflow.ainvoke({
            "job_id": job_id,
            "topic": topic,
            "instruction": instruction or topic,
            "iteration": 0,
            "results": [],
        })

        log.info("리서치 워크플로우 완료: job_id=%s", job_id)

        return {
            "job_id": job_id,
            "status": "completed",
            "topic": topic,
            "final_report": result.get("final_report", ""),
            "results_count": len(result.get("results", [])),
            "iterations": result.get("iteration", 0),
        }
    except Exception as exc:
        log.error("리서치 워크플로우 실패: job_id=%s, error=%s", job_id, exc, exc_info=True)
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(exc),
        }
