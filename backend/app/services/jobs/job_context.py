"""추적 메타 & 타이머(§14.2, §18).

워커는 추적 메타를 ``JobContext`` 로 묶고 ``ctx.callback_kwargs()`` 로 콜백 인자를 만든다.
시간 측정은 ``JobTimer`` → ``timer.elapsed()``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobContext:
    """Job 추적 메타 묶음(§18.3: request_id/trace_id/step_id/job_type/worker_id)."""

    job_id: str
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    step_id: Optional[str] = None
    job_type: Optional[str] = None
    worker_id: Optional[str] = None

    def callback_kwargs(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "step_id": self.step_id,
            "job_type": self.job_type,
            "worker_id": self.worker_id,
        }


@dataclass
class JobTimer:
    """경과 시간 측정기. ``elapsed()`` 는 표준 timing 포맷을 반환한다."""

    started_at: str = field(default_factory=_utc_now_iso)
    _t0: float = field(default_factory=time.perf_counter)

    def elapsed(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": _utc_now_iso(),
            "latency_ms": round((time.perf_counter() - self._t0) * 1000, 2),
        }
