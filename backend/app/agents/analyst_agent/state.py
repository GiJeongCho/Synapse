"""AnalystAgentState — 기획 확정 후 필드 정의(§5)."""

from __future__ import annotations

from typing import TypedDict


class AnalystAgentState(TypedDict, total=False):
    job_id: str
    # TODO: material, analysis, critique, iteration ...
