"""도메인 공통 Base State(§5.2)."""

from __future__ import annotations

from typing import Optional, TypedDict


class BaseAgentState(TypedDict, total=False):
    job_id: str
    error: Optional[str]
    iteration: int
