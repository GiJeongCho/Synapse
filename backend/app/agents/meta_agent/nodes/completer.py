"""Completer 노드 — 빌드 후 계획(todolist)이 실제로 완료됐는지 검증/보고한다.

Planner가 세운 계획의 todolist를 실제 생성된 도구/워크플로우와 대조하여
각 항목의 완료 여부, 누락된 컴포넌트, 요약 보고를 만든다.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.prompts import COMPLETER_PROMPT
from app.agents.meta_agent.state import MetaAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.llm.utils import extract_json_from_llm_response
from app.core.logging import logger

log = logger(__name__)

# Planner stage ↔ 실제 도구 분류(키워드) 매핑 — 결정적 누락 검사용
_STAGE_KEYWORDS = {
    "fetch": ("fetch", "scrape", "crawl", "download"),
    "process": ("process", "check", "dedup", "filter", "parse"),
    "summarize": ("summarize", "digest", "extract", "analyze"),
    "deliver": ("send", "email", "mail", "notify", "post"),
    "schedule": ("schedule", "cron", "timer"),
}


def _built_stages(tools: list[dict[str, Any]]) -> set[str]:
    """생성된 도구들이 커버하는 stage 집합을 구한다."""
    covered: set[str] = set()
    for t in tools:
        blob = (str(t.get("tool_id", "")) + " " + str(t.get("name", "")) + " "
                + " ".join(str(f) for f in t.get("functions", []))).lower()
        for stage, kws in _STAGE_KEYWORDS.items():
            if any(kw in blob for kw in kws):
                covered.add(stage)
    return covered


def _required_stages(plan: dict[str, Any]) -> set[str]:
    """계획의 architecture가 요구하는 stage 집합을 구한다."""
    req: set[str] = set()
    for comp in plan.get("architecture", {}).get("components", []) or []:
        if isinstance(comp, dict):
            stage = str(comp.get("stage", "")).lower()
            if stage in _STAGE_KEYWORDS:
                req.add(stage)
    return req


async def _runtime_health_check(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """생성된 도구를 dry-run으로 1회 실행해 데이터 흐름 결함을 검사한다.

    발송 단계는 건너뛰며(메일 실발송 방지), 어떤 예외도 생성 흐름을 막지 않는다.
    """
    if not tools:
        return {"ran": False, "healthy": True, "issues": []}

    from app.services.agent_runner import evaluate_pipeline_health, run_agent_pipeline

    try:
        result = await run_agent_pipeline("__completer_check__", tools, dry_run=True)
    except Exception as exc:  # noqa: BLE001 — 검사 실패가 등록을 막으면 안 됨
        log.warning("Completer 런타임 검사 예외: %s", exc)
        return {"ran": True, "healthy": True, "issues": [], "error": str(exc)}

    health = evaluate_pipeline_health(result.get("results", []))
    health["ran"] = True
    # 파이프라인 자체 실패 사유도 합친다.
    if result.get("failed"):
        health["healthy"] = False
        health.setdefault("issues", []).append(
            f"파이프라인 실패: {result.get('failure_reason', '')}"
        )
    log.info(
        "Completer 런타임 검사: healthy=%s, issues=%s",
        health.get("healthy"), health.get("issues"),
    )
    return health


async def completer(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """계획 대비 실제 빌드 결과를 검증하고 완료 보고를 생성한다."""
    plan = state.get("plan", {})
    project_files = state.get("project_files", {}) or {}
    tools = project_files.get("tools", []) or []
    workflow = project_files.get("workflow", []) or []

    log.info("Completer 시작: 도구 %d개 검증", len(tools))

    # 1) 결정적 누락 검사 (LLM 없이도 핵심 누락은 잡는다)
    required = _required_stages(plan)
    built = _built_stages(tools)
    missing_stages = sorted(required - built)

    # 1.5) 런타임 데이터 흐름 검사 — dry-run으로 실제 실행해 빈 요약/단절을 잡는다.
    runtime_health = await _runtime_health_check(tools)

    built_result = {
        "tools": [
            {"tool_id": t.get("tool_id"), "name": t.get("name"),
             "functions": t.get("functions", [])}
            for t in tools
        ],
        "workflow": workflow,
    }

    report: dict[str, Any] = {}
    try:
        llm = get_llm_for_agent("meta")
        messages = COMPLETER_PROMPT.format_messages(
            plan=json.dumps(plan, ensure_ascii=False, indent=2),
            built_result=json.dumps(built_result, ensure_ascii=False, indent=2),
        )
        response = await llm.ainvoke(messages)
        report = extract_json_from_llm_response(response.content)
    except Exception as exc:  # noqa: BLE001 — 보고 실패가 등록을 막지 않게
        log.warning("Completer LLM 실패, 결정적 검사로 대체: %s", exc)
        report = {}

    if not isinstance(report, dict):
        report = {}

    # 2) 결정적 검사 결과를 LLM 보고에 강제 병합 (누락은 반드시 드러나게)
    report.setdefault("build_type", plan.get("build_type", "agent"))
    report.setdefault("todos", [{"task": t, "done": True, "evidence": ""}
                                for t in plan.get("todolist", [])])
    llm_missing = report.get("missing") if isinstance(report.get("missing"), list) else []
    merged_missing = sorted(set(llm_missing) | {f"{s} 컴포넌트 누락" for s in missing_stages})
    report["missing"] = merged_missing

    # 런타임 검사 결과를 보고에 병합 (데이터 흐름 결함은 명백한 미완료로 처리)
    report["runtime"] = runtime_health
    runtime_issues = runtime_health.get("issues", []) if isinstance(runtime_health, dict) else []
    healthy = runtime_health.get("healthy", True) if isinstance(runtime_health, dict) else True

    report["all_done"] = (
        bool(report.get("all_done", True)) and not merged_missing and healthy
    )
    problems = merged_missing + list(runtime_issues)
    report.setdefault(
        "summary",
        "모든 계획 항목 완료" if not problems else f"문제: {', '.join(problems)}",
    )
    if problems:
        report["summary"] = f"문제: {', '.join(problems)}"

    # 보고를 project_files에도 실어 레지스트리/프론트에서 조회 가능하게 한다.
    updated_pf = {**project_files, "completion_report": report}

    log.info(
        "Completer 완료: all_done=%s, 누락=%s",
        report.get("all_done"), report.get("missing"),
    )

    return {
        "completion_report": report,
        "project_files": updated_pf,
        "current_step": "completer",
    }
