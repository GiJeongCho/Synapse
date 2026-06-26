"""에이전트 파이프라인 실행기.

생성된 에이전트의 MCP 도구를 순서대로 실행하며,
이전 도구의 출력을 다음 도구의 입력으로 자동 연결한다.
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.core.config import settings
from app.core.logging import logger
from app.services.mcp.tool_runtime import execute_tool

log = logger(__name__)

PIPELINE_ORDER_KEYWORDS = [
    ["fetch", "scrape", "crawl", "get", "download"],
    ["check", "freshness", "validate", "filter"],
    ["summarize", "extract", "parse", "analyze"],
    ["send", "email", "mail", "notify", "post"],
    ["schedule", "cron", "timer"],
]


def _sort_tools_for_pipeline(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """도구를 파이프라인 순서에 맞게 정렬한다."""
    def _priority(tool: dict) -> int:
        name = tool.get("tool_id", "").lower()
        for fn in tool.get("functions", []):
            name += " " + fn.lower()

        for idx, keywords in enumerate(PIPELINE_ORDER_KEYWORDS):
            if any(kw in name for kw in keywords):
                return idx
        return 99

    return sorted(tools, key=_priority)


def _get_env_for_tools() -> dict[str, str]:
    """도구 실행 시 전달할 환경변수를 수집한다."""
    env = dict(os.environ)
    env["SMTP_HOST"] = settings.smtp_host
    env["SMTP_PORT"] = str(settings.smtp_port)
    env["SMTP_USER"] = settings.smtp_user
    env["SMTP_PASSWORD"] = settings.smtp_password
    env["SMTP_FROM"] = settings.smtp_from or settings.smtp_user
    return env


async def run_agent_pipeline(
    agent_id: str,
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    """에이전트의 도구를 파이프라인으로 실행한다.

    실행 순서: fetch/crawl → check → summarize → send_email → schedule
    이전 도구의 출력을 다음 도구의 첫 번째 인자로 전달.
    """
    sorted_tools = _sort_tools_for_pipeline(tools)
    env = _get_env_for_tools()

    log.info("파이프라인 실행 시작: agent=%s, 도구 %d개", agent_id, len(sorted_tools))

    results = []
    prev_output: Any = None
    skip_rest = False

    for tool in sorted_tools:
        tool_id = tool["tool_id"]
        functions = tool.get("functions", [])

        for func_name in functions:
            if func_name.startswith("schedule"):
                results.append({
                    "tool_id": tool_id,
                    "function": func_name,
                    "result": {"status": "skipped", "reason": "스케줄 설정은 스케줄 페이지에서 관리"},
                })
                continue

            if skip_rest:
                results.append({
                    "tool_id": tool_id,
                    "function": func_name,
                    "result": {"status": "skipped", "reason": "이전 단계 실패로 건너뜀"},
                })
                continue

            args = _build_args_from_prev(func_name, prev_output)

            result = await execute_tool(
                tool_id, func_name, arguments=args, timeout=120, env_vars=env,
            )

            results.append({
                "tool_id": tool_id,
                "function": func_name,
                "result": result,
            })

            if result.get("status") == "success":
                inner = result.get("result", {})
                prev_output = inner

                if isinstance(inner, dict) and inner.get("is_fresh") is False:
                    skip_rest = True
                    log.info("중복 콘텐츠 감지 — 나머지 단계 건너뜀")
            else:
                skip_rest = True
                log.warning("도구 실행 실패: %s/%s, 나머지 건너뜀", tool_id, func_name)

    all_success = all(
        r["result"].get("status") in ("success", "skipped")
        for r in results
    )

    return {
        "status": "success" if all_success else "partial_failure",
        "agent_id": agent_id,
        "results": results,
    }


def _build_args_from_prev(func_name: str, prev_output: Any) -> dict[str, Any]:
    """이전 도구의 출력에서 현재 함수에 맞는 인자를 추출한다."""
    if prev_output is None:
        return {}

    fn = func_name.lower()

    if not isinstance(prev_output, dict):
        prev_output = {"output": str(prev_output)}

    if "summarize" in fn or "extract" in fn or "parse" in fn:
        content = prev_output.get("content") or prev_output.get("output") or prev_output.get("text", "")
        if content:
            return {"html_content": content}

    if "check" in fn or "freshness" in fn:
        content = prev_output.get("content") or prev_output.get("output") or prev_output.get("text", "")
        if content:
            return {"content_text": content}

    if "send" in fn or "email" in fn or "mail" in fn:
        summary = prev_output.get("summary") or prev_output.get("output") or prev_output.get("text", "")
        if summary:
            return {"summary_text": summary}

    return {}
