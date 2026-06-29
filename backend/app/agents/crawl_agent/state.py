"""CrawlAgentState(§5)."""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class CrawlAgentState(TypedDict, total=False):
    job_id: str
    url: str
    raw_content: str
    extracted_text: str
    normalized_text: str
    metadata: dict[str, Any]
    error: Optional[str]
