"""Shared state definition for the LangGraph multi-agent system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchState:
    """Mutable state object passed through the agent graph."""

    # Input
    query: str = ""
    domain_filter: str | None = None  # paper / news / law / None

    # Orchestrator decisions
    tasks: list[str] = field(default_factory=list)
    current_step: str = ""
    iteration: int = 0
    max_iterations: int = 5

    # Search results
    search_results: list[dict[str, Any]] = field(default_factory=list)
    crawl_results: list[dict[str, Any]] = field(default_factory=list)

    # Graph exploration
    graph_insights: list[dict[str, Any]] = field(default_factory=list)

    # Analysis
    analysis: str = ""
    sufficiency_score: float = 0.0

    # Final report
    report: str = ""

    # Status
    is_complete: bool = False
    error: str | None = None
