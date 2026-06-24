"""GraphAgentState(§5)."""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class GraphAgentState(TypedDict, total=False):
    job_id: str
    query: str
    context: list[dict[str, Any]]
    expanded_context: str
    summary: str
    error: Optional[str]
