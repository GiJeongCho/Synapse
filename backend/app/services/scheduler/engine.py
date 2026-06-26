"""에이전트 스케줄러 엔진 — APScheduler 기반 자동 실행.

등록된 에이전트의 스케줄에 따라 MCP 도구를 자동 실행한다.
실행 결과는 로그 파일로 저장된다.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging import logger

log = logger(__name__)

_LOG_DIR = Path(settings.upload_dir).parent / "schedule_logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_SCHEDULES_FILE = Path(settings.upload_dir).parent / "schedules.json"

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    return _scheduler


def _load_schedules() -> list[dict[str, Any]]:
    if _SCHEDULES_FILE.exists():
        try:
            return json.loads(_SCHEDULES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_schedules(schedules: list[dict[str, Any]]) -> None:
    _SCHEDULES_FILE.write_text(
        json.dumps(schedules, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _run_agent_tools(schedule_id: str, agent_id: str, tools: list[dict]) -> None:
    """스케줄에 의해 호출 — 에이전트 파이프라인을 실행한다."""
    from app.services.agent_runner import run_agent_pipeline

    ts = datetime.now(timezone.utc).isoformat()
    log.info("스케줄 실행 시작: %s (agent=%s)", schedule_id, agent_id)

    pipeline_result = await run_agent_pipeline(agent_id, tools)
    results = pipeline_result.get("results", [])

    log_entry = {
        "schedule_id": schedule_id,
        "agent_id": agent_id,
        "started_at": ts,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_status": pipeline_result.get("status", "unknown"),
        "results": results,
    }

    log_file = _LOG_DIR / f"{schedule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_file.write_text(json.dumps(log_entry, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("스케줄 실행 완료: %s, 결과 %d건 → %s", schedule_id, len(results), log_file.name)


def register_schedule(
    agent_id: str,
    cron_expression: str,
    tools: list[dict],
    description: str = "",
) -> dict[str, Any]:
    """새로운 스케줄을 등록한다.

    cron_expression: "분 시 일 월 요일" 형식 (예: "10 9 * * *" = 매일 9:10)
    """
    scheduler = get_scheduler()
    schedule_id = f"sched_{agent_id}"

    parts = cron_expression.strip().split()
    if len(parts) < 5:
        raise ValueError(f"잘못된 cron 형식: '{cron_expression}' (분 시 일 월 요일)")

    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone="Asia/Seoul",
    )

    existing = scheduler.get_job(schedule_id)
    if existing:
        scheduler.remove_job(schedule_id)

    scheduler.add_job(
        _run_agent_tools,
        trigger=trigger,
        id=schedule_id,
        args=[schedule_id, agent_id, tools],
        name=f"Agent: {agent_id}",
        replace_existing=True,
    )

    schedule_data = {
        "schedule_id": schedule_id,
        "agent_id": agent_id,
        "cron": cron_expression,
        "description": description,
        "tools": tools,
        "enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    schedules = _load_schedules()
    schedules = [s for s in schedules if s["schedule_id"] != schedule_id]
    schedules.append(schedule_data)
    _save_schedules(schedules)

    log.info("스케줄 등록: %s, cron=%s", schedule_id, cron_expression)
    return schedule_data


def remove_schedule(schedule_id: str) -> bool:
    """스케줄을 해제한다."""
    scheduler = get_scheduler()

    try:
        scheduler.remove_job(schedule_id)
    except Exception:
        pass

    schedules = _load_schedules()
    before = len(schedules)
    schedules = [s for s in schedules if s["schedule_id"] != schedule_id]
    _save_schedules(schedules)

    removed = len(schedules) < before
    if removed:
        log.info("스케줄 해제: %s", schedule_id)
    return removed


def list_schedules() -> list[dict[str, Any]]:
    """등록된 모든 스케줄 목록을 반환한다."""
    scheduler = get_scheduler()
    schedules = _load_schedules()

    for s in schedules:
        job = scheduler.get_job(s["schedule_id"])
        if job:
            s["next_run"] = str(job.next_run_time) if job.next_run_time else None
            s["active"] = True
        else:
            s["next_run"] = None
            s["active"] = False

    return schedules


def get_schedule_logs(schedule_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """특정 스케줄의 실행 로그를 반환한다."""
    logs = []
    if not _LOG_DIR.exists():
        return logs

    log_files = sorted(
        [f for f in _LOG_DIR.iterdir() if f.name.startswith(schedule_id)],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    for lf in log_files[:limit]:
        try:
            entry = json.loads(lf.read_text(encoding="utf-8"))
            logs.append(entry)
        except (json.JSONDecodeError, OSError):
            pass

    return logs


def startup() -> None:
    """서버 시작 시 저장된 스케줄을 복원하고 스케줄러를 시작한다."""
    scheduler = get_scheduler()
    schedules = _load_schedules()

    restored = 0
    for s in schedules:
        if not s.get("enabled", True):
            continue
        try:
            parts = s["cron"].strip().split()
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone="Asia/Seoul",
            )
            scheduler.add_job(
                _run_agent_tools,
                trigger=trigger,
                id=s["schedule_id"],
                args=[s["schedule_id"], s["agent_id"], s["tools"]],
                name=f"Agent: {s['agent_id']}",
                replace_existing=True,
            )
            restored += 1
        except Exception as exc:
            log.warning("스케줄 복원 실패: %s — %s", s["schedule_id"], exc)

    if not scheduler.running:
        scheduler.start()

    log.info("스케줄러 시작: %d개 스케줄 복원", restored)


def shutdown() -> None:
    """서버 종료 시 스케줄러를 정리한다."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("스케줄러 종료")
