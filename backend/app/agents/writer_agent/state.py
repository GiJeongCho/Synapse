"""WriterAgentState(§5)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class WriterAgentState(TypedDict, total=False):
    job_id: str
    topic: str
    sources: list[dict[str, Any]]
    outline: str
    draft: str
    evaluation: dict[str, Any]
    final_text: str
    iteration: int
    error: Optional[str]
    messages: Annotated[list[dict[str, Any]], operator.add]
