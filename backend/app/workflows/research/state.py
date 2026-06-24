"""ResearchState — Supervisor 워크플로우 상태(§5)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class ResearchState(TypedDict, total=False):
    job_id: str
    topic: str
    instruction: str
    next_agent: str
    results: Annotated[list[dict[str, Any]], operator.add]
    search_result: Optional[dict[str, Any]]
    crawl_result: Optional[dict[str, Any]]
    graph_result: Optional[dict[str, Any]]
    analyst_result: Optional[dict[str, Any]]
    writer_result: Optional[dict[str, Any]]
    final_report: str
    iteration: int
    error: Optional[str]
    messages: Annotated[list[dict[str, Any]], operator.add]
