"""ResearchState — Supervisor 워크플로우 상태(§5).

기획 확정 후 topic, next, instruction, 워커 산출 필드 등을 정의한다.
"""

from __future__ import annotations

from typing import TypedDict


class ResearchState(TypedDict, total=False):
    job_id: str
    # TODO: topic, next, instruction, search_result, report, ...
