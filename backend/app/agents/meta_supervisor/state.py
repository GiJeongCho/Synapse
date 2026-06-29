"""DualSupervisorState — 쌍방 Supervisor 오케스트레이션 State(§5)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


class AgentRegistryRecord(TypedDict, total=False):
    """Agent Registry에 저장되는 에이전트 레코드."""

    agent_id: str
    user_request: str
    request_embedding: list[float]
    agent_spec: dict[str, Any]
    system_prompt: str
    mcp_tools: list[dict[str, Any]]
    project_files: dict[str, str]
    test_result: dict[str, Any]
    created_at: str
    version: int
    mode: str  # "solo" | "dual"


class DualSupervisorState(TypedDict, total=False):
    """쌍방 Supervisor 루프 + Registry 조회를 포괄하는 최상위 State."""

    job_id: str
    user_request: str

    # 실행 모드
    critic_enabled: bool

    # Agent Registry
    registry_hit: bool
    registry_match: Optional[AgentRegistryRecord]
    registry_similarity: float

    # 요구사항 분석 결과 (파이프라인 입력)
    agent_spec: dict[str, Any]

    # 라운드 추적
    round: int
    max_rounds: int
    history: Annotated[list[dict[str, Any]], operator.add]

    # Supervisor-A (Builder) 산출물
    current_result: Optional[dict[str, Any]]
    builder_strategy: dict[str, Any]
    counter_review: Optional[dict[str, Any]]

    # Supervisor-B (Critic) 산출물
    evaluation: Optional[dict[str, Any]]
    improvement_plan: Optional[dict[str, Any]]
    eval_criteria: dict[str, Any]

    # 합의
    is_agreed: bool
    best_result: Optional[dict[str, Any]]
    stale_count: int

    error: Optional[str]
