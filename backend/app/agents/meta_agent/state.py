"""MetaAgentState — 에이전트 생성 파이프라인 State(§5)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class MetaAgentState(TypedDict, total=False):
    """Supervisor-A(Builder)가 호출하는 에이전트 생성 파이프라인의 State."""

    job_id: str
    user_request: str

    # Requirements Analyzer
    agent_spec: dict[str, Any]

    # Planner — 도구/에이전트 판단 + todolist + 구조 설계
    plan: dict[str, Any]

    # Tool Retriever
    mcp_tools: list[dict[str, Any]]

    # Provisioner
    system_prompt: str
    project_files: dict[str, str]

    # Evaluator
    test_result: dict[str, Any]
    retry_count: int

    # Completer — todolist 대조 완료 검증/보고
    completion_report: dict[str, Any]

    current_step: str
    error: Optional[str]
    messages: Annotated[list[dict[str, Any]], operator.add]
