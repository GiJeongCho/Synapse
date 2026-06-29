"""SearchAgentState(§5)."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class SearchAgentState(TypedDict, total=False):
    job_id: str
    query: str
    raw_results: list[dict[str, Any]]
    filtered_results: list[dict[str, Any]]
    organized: list[dict[str, Any]]
    evaluation: dict[str, Any]
    iteration: int
    error: Optional[str]
    messages: Annotated[list[dict[str, Any]], operator.add]
