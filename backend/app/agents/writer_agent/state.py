"""WriterAgentState — 기획 확정 후 필드 정의(§5)."""

from __future__ import annotations

from typing import TypedDict


class WriterAgentState(TypedDict, total=False):
    job_id: str
    # TODO: text_input, task_list, draft, evaluation_result, final_output, iteration ...
