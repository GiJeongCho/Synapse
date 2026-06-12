"""SearchAgentState — 기획 확정 후 TypedDict 필드를 정의한다(§5)."""

from __future__ import annotations

from typing import TypedDict


class SearchAgentState(TypedDict, total=False):
    job_id: str
    # TODO: query, raw_results, filtered_results, organized, evaluation, iteration ...
