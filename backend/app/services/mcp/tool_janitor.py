"""도구 청소부(Tool Janitor) — 에이전트 삭제 시 어떤 도구를 지울지 판단한다.

2단계로 동작한다.
  1) 하드 규칙으로 '절대 지우면 안 되는' 도구를 보호한다.
     - 공용 도구(shared_tools, universal_parser/site_parser 등)
     - metadata 에 essential=true 로 표시된 필수 도구
     - 다른 에이전트가 참조 중인 도구
  2) 남은 회색지대는 LLM 심판(하네스로 감쌈)이 delete/keep 을 판단한다.
     - 이 에이전트 전용 도구 → delete
     - 범용·재사용 가능 유틸리티 → keep
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.agents.meta_agent.harness import ainvoke_json
from app.core.config import settings
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger
from app.services.mcp.tool_runtime import list_tools

log = logger(__name__)

_JUDGE_SYSTEM = """You are a cleanup judge. An agent is being DELETED. Decide, for each \
candidate MCP tool, whether to DELETE it or KEEP it.

Guidelines:
- DELETE tools that are specific to this single agent (its custom fetch / summarize / \
email steps that no other agent would reuse).
- KEEP tools that are generic, reusable utilities other agents would likely want \
(e.g. a generic web/RSS parser, a generic translator, a generic mailer).
- When unsure, prefer DELETE — the agent is gone and leftover clutter is undesirable.

Return ONLY JSON, no prose:
{{"decisions": [{{"tool_id": "<id>", "action": "delete" | "keep", "reason": "<short>"}}]}}"""

_JUDGE_HUMAN = """Agent being deleted: {agent_id}

Candidate tools (protected tools already removed from this list):
{candidates}

Decide delete/keep for EVERY tool above."""

_JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [("system", _JUDGE_SYSTEM), ("human", _JUDGE_HUMAN)]
)


def _tools_used_by_other_agents(own_ids: set[str]) -> set[str]:
    """삭제 대상이 아닌 다른 에이전트가 참조하는 tool_id 집합을 반환한다."""
    used: set[str] = set()
    try:
        from app.services.agent_registry import store as registry_store

        rows = registry_store.list_all()
    except Exception as exc:  # noqa: BLE001 — 조회 실패 시 보호 못 해도 삭제는 진행
        log.warning("타 에이전트 도구 조회 실패: %s", exc)
        return used

    for row in rows:
        if row.get("agent_id") in own_ids:
            continue
        pf = row.get("project_files")
        if isinstance(pf, str):
            try:
                pf = json.loads(pf)
            except (ValueError, TypeError):
                pf = None
        if isinstance(pf, dict):
            for t in pf.get("tools", []):
                if isinstance(t, dict) and t.get("tool_id"):
                    used.add(t["tool_id"])
    return used


async def judge_tool_deletions(
    agent_id: str,
    stored_agent_id: str,
    candidate_tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """후보 도구를 보호/삭제로 분류한다.

    반환: {
        "delete":       [tool_id, ...],          # 실제 삭제할 도구
        "protected":    [{tool_id, reason}, ...],# 하드 규칙으로 보호
        "kept_by_judge":[{tool_id, reason}, ...],# 심판이 재사용 가능 판단
    }
    """
    shared_ids = {t["tool_id"] for t in list_tools() if t.get("shared")}
    used_by_others = _tools_used_by_other_agents({agent_id, stored_agent_id})

    protected: list[dict[str, str]] = []
    gray: list[dict[str, Any]] = []

    for t in candidate_tools:
        tid = t["tool_id"]
        if tid in shared_ids or bool(t.get("essential")):
            protected.append({"tool_id": tid, "reason": "공용/필수 도구"})
        elif tid in used_by_others:
            protected.append({"tool_id": tid, "reason": "다른 에이전트가 사용 중"})
        else:
            gray.append(t)

    to_delete: list[str] = []
    kept_by_judge: list[dict[str, str]] = []

    if gray:
        llm = get_llm_for_agent("meta")
        messages = _JUDGE_PROMPT.format_messages(
            agent_id=agent_id,
            candidates=json.dumps(
                [
                    {
                        "tool_id": t["tool_id"],
                        "functions": t.get("functions", []),
                        "description": t.get("description", ""),
                    }
                    for t in gray
                ],
                ensure_ascii=False,
                indent=2,
            ),
        )
        # 파싱 실패/타임아웃 시: 회색지대는 전부 삭제(기존 동작과 동일하게 정리)
        fallback = {
            "decisions": [
                {"tool_id": t["tool_id"], "action": "delete", "reason": "기본 정리"}
                for t in gray
            ]
        }
        verdict = await ainvoke_json(
            llm, messages, node="tool_janitor", retries=1, fallback=fallback,
        )
        decisions = {
            d.get("tool_id"): d
            for d in verdict.get("decisions", [])
            if isinstance(d, dict)
        }
        for t in gray:
            d = decisions.get(t["tool_id"]) or {"action": "delete"}
            if d.get("action") == "keep":
                kept_by_judge.append(
                    {"tool_id": t["tool_id"], "reason": d.get("reason", "재사용 가능 판단")}
                )
            else:
                to_delete.append(t["tool_id"])

    log.info(
        "도구 심판 완료: 삭제 %d, 보호 %d, 심판보존 %d (agent=%s)",
        len(to_delete), len(protected), len(kept_by_judge), agent_id,
    )
    return {
        "delete": to_delete,
        "protected": protected,
        "kept_by_judge": kept_by_judge,
    }
