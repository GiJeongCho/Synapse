"""AnalystAgentState(§5)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class AnalystAgentState(TypedDict, total=False):
    job_id: str
    topic: str
    sources: list[dict[str, Any]]
    analysis: str
    critique: str
    refined_analysis: str
    iteration: int
    error: Optional[str]
    messages: Annotated[list[dict[str, Any]], operator.add]
