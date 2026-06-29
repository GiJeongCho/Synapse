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
    """도구를 파이프라인 순서에 맞게 정렬한다.

    에이전트 접두사("{agent}__")는 키워드 매칭을 오염시키므로 제거하고,
    함수 이름 + 접미사만으로 단계를 판정한다.
    """
    def _priority(tool: dict) -> int:
        tool_id = tool.get("tool_id", "").lower()
        suffix = tool_id.split("__", 1)[-1]  # 에이전트 접두사 제거
        name = suffix
        for fn in tool.get("functions", []):
            name += " " + fn.lower()

        for idx, keywords in enumerate(PIPELINE_ORDER_KEYWORDS):
            if any(kw in name for kw in keywords):
                return idx
        return 99

    return sorted(tools, key=_priority)


def _get_env_for_tools() -> dict[str, str]:
    """도구 실행 시 전달할 환경변수를 수집한다.

    pydantic settings(.env)의 값은 os.environ에 없을 수 있으므로
    SMTP·LLM API 키를 명시적으로 주입한다.
    """
    env = dict(os.environ)
    env["SMTP_HOST"] = settings.smtp_host
    env["SMTP_PORT"] = str(settings.smtp_port)
    env["SMTP_USER"] = settings.smtp_user
    env["SMTP_PASSWORD"] = settings.smtp_password
    env["SMTP_FROM"] = settings.smtp_from or settings.smtp_user

    # LLM API 키 — 설정에 값이 있을 때만 주입 (빈 값으로 덮어쓰지 않음)
    for env_name, value in (
        ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        ("OPENAI_API_KEY", settings.openai_api_key),
        ("GEMINI_API_KEY", settings.gemini_api_key),
    ):
        if value:
            env[env_name] = value
    return env


_SIDE_EFFECT_KEYWORDS = ("send", "email", "mail", "notify", "post")


def _is_side_effect_tool(tool_id: str, func_name: str) -> bool:
    """발송/알림 등 부작용이 있는 도구인지 판정한다."""
    name = tool_id.split("__", 1)[-1].lower() + " " + func_name.lower()
    return any(kw in name for kw in _SIDE_EFFECT_KEYWORDS)


# 런타임 하네스 — 일시적 실패(타임아웃/네트워크)는 재시도한다.
_RUNTIME_RETRIES = 1
_TRANSIENT_MARKERS = (
    "timeout", "timed out", "connection", "temporarily", "temporary",
    "network", "reset", "unreachable", "503", "502", "504",
    "econn", "name or service", "no address", "getaddrinfo",
)


def _is_transient_failure(result: dict[str, Any]) -> bool:
    """재시도하면 회복될 수 있는 일시적 실패인지 판정한다 (코드 버그는 제외)."""
    status = result.get("status")
    if status == "timeout":
        return True
    if status == "error":
        err = str(
            result.get("error_message")
            or result.get("error")
            or result.get("stderr")
            or ""
        ).lower()
        return any(k in err for k in _TRANSIENT_MARKERS)
    return False


async def _execute_with_harness(
    tool_id: str,
    func_name: str,
    args: dict[str, Any],
    env: dict[str, str],
    *,
    timeout: float,
    allow_retry: bool = True,
    retries: int = _RUNTIME_RETRIES,
) -> dict[str, Any]:
    """execute_tool 을 감싸 일시적 실패를 재시도하는 런타임 하네스.

    발송/알림 등 부작용 도구는 중복 실행을 막기 위해 재시도하지 않는다.
    """
    result = await execute_tool(
        tool_id, func_name, arguments=args, timeout=timeout, env_vars=env,
    )
    attempt = 0
    while allow_retry and attempt < retries and _is_transient_failure(result):
        attempt += 1
        log.warning(
            "런타임 하네스 재시도 %d/%d: %s/%s (%s)",
            attempt, retries, tool_id, func_name, result.get("status"),
        )
        result = await execute_tool(
            tool_id, func_name, arguments=args, timeout=timeout, env_vars=env,
        )
    return result


async def run_agent_pipeline(
    agent_id: str,
    tools: list[dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """에이전트의 도구를 파이프라인으로 실행한다.

    실행 순서: fetch/crawl → check → summarize → send_email → schedule
    이전 도구의 출력을 다음 도구의 첫 번째 인자로 전달.

    dry_run=True이면 발송/알림 계열 도구는 실제 실행하지 않고 건너뛴다
    (에이전트 생성 중 smoke test에서 메일이 실제로 나가는 것을 방지).
    """
    sorted_tools = _sort_tools_for_pipeline(tools)
    env = _get_env_for_tools()

    log.info(
        "파이프라인 실행 시작: agent=%s, 도구 %d개%s",
        agent_id, len(sorted_tools), " (dry-run)" if dry_run else "",
    )

    results = []
    carry: dict[str, Any] = {}  # 파이프라인 전체에서 본문/요약을 누적 보존
    skip_rest = False
    failure_reason = ""

    for tool in sorted_tools:
        tool_id = tool["tool_id"]
        functions = tool.get("functions", [])

        for func_name in functions:
            if func_name.startswith("schedule"):
                results.append({
                    "tool_id": tool_id,
                    "function": func_name,
                    "result": {"status": "skipped"},
                    "reason": "스케줄 설정은 스케줄 페이지에서 관리",
                })
                continue

            if dry_run and _is_side_effect_tool(tool_id, func_name):
                results.append({
                    "tool_id": tool_id,
                    "function": func_name,
                    "result": {"status": "skipped"},
                    "reason": "dry-run: 발송 단계 생략",
                })
                continue

            if skip_rest:
                results.append({
                    "tool_id": tool_id,
                    "function": func_name,
                    "result": {"status": "skipped"},
                    "reason": "이전 단계 실패로 건너뜀",
                })
                continue

            args = _build_context_from_prev(carry)

            result = await _execute_with_harness(
                tool_id, func_name, args, env, timeout=120,
                allow_retry=not _is_side_effect_tool(tool_id, func_name),
            )

            entry = {"tool_id": tool_id, "function": func_name, "result": result}

            if result.get("status") == "success":
                inner = result.get("result", {})
                _accumulate_carry(carry, inner)

                ok, reason = _diagnose_step(func_name, inner)
                if not ok:
                    # 서브프로세스는 정상 종료했지만 실질적으로 실패한 경우
                    result["status"] = "error"
                    entry["reason"] = reason
                    skip_rest = True
                    failure_reason = failure_reason or f"{func_name}: {reason}"
                    log.warning("도구 실질 실패: %s/%s — %s", tool_id, func_name, reason)
                elif isinstance(inner, dict) and inner.get("is_fresh") is False:
                    skip_rest = True
                    entry["reason"] = "중복 콘텐츠 — 변경 없음"
                    log.info("중복 콘텐츠 감지 — 나머지 단계 건너뜀")
            else:
                reason = _format_error_reason(result)
                entry["reason"] = reason
                # 구조화된 위치 정보가 있으면 함께 보존 (프론트에서 상세 표시)
                for key in ("error_type", "error_message", "line", "code", "stage", "traceback"):
                    if key in result:
                        entry[key] = result[key]
                skip_rest = True
                failure_reason = failure_reason or f"[{tool_id}/{func_name}] {reason}"
                log.warning("도구 실행 실패: %s/%s — %s", tool_id, func_name, reason)

            results.append(entry)

    failed = bool(failure_reason)

    return {
        "status": "partial_failure" if failed else "success",
        "failed": failed,
        "failure_reason": failure_reason,
        "agent_id": agent_id,
        "results": results,
    }


_PROCESS_KEYWORDS = ("summarize", "digest", "extract", "analyze", "parse", "process")

# LLM이 "본문이 없다/달라"며 요약을 거부할 때 나타나는 문구 (요약 실패로 간주)
_REFUSAL_MARKERS = (
    "본문에 접근할 수 없", "본문이 필요", "기사 내용이나 요약을 제공",
    "기사 전문", "내용을 제공해 주", "제목만 볼 수 있",
    "i don't see", "i do not see", "please provide", "i can only see",
    "cannot access", "unable to access", "need the actual",
)


def _looks_like_refusal(text: str) -> bool:
    """요약문이 '본문을 달라'는 LLM 거부 응답인지 판정한다."""
    low = text.lower()
    return any(m.lower() in low for m in _REFUSAL_MARKERS)


def evaluate_pipeline_health(results: list[dict[str, Any]]) -> dict[str, Any]:
    """dry-run 파이프라인 결과에서 '데이터 흐름 단절' 같은 로직 결함을 진단한다.

    생성 시점 검사용. 실제 발송 없이도 다음을 잡아낸다:
    - fetch가 본문/기사를 못 가져옴
    - summarize/process 단계가 입력은 있는데 빈 요약을 냄 (전달 단절·short-circuit 의심)
    - 발송할 콘텐츠가 파이프라인 어디에서도 생성되지 않음
    """
    issues: list[str] = []
    fetched_something = False
    produced_content = False
    saw_fetch = False
    saw_process = False

    for r in results:
        fn = str(r.get("function", "")).lower()
        outer = r.get("result") or {}
        status = str(outer.get("status", "")).lower()
        inner = outer.get("result") if isinstance(outer, dict) else {}
        if not isinstance(inner, dict):
            inner = {}
        if status == "skipped":
            continue

        is_fetch = any(k in fn for k in _FETCH_KEYWORDS)
        is_process = any(k in fn for k in _PROCESS_KEYWORDS)

        if is_fetch:
            saw_fetch = True
            if inner.get("content") or inner.get("articles"):
                fetched_something = True
            else:
                issues.append(f"{fn}: 콘텐츠/기사를 가져오지 못함")

        if is_process:
            saw_process = True
            summ = ""
            if isinstance(inner, dict):
                summ = str(inner.get("summary") or inner.get("content") or "").strip()
            if not summ:
                issues.append(
                    f"{fn}: 요약 결과가 비어 있음 — fetch→summarize 데이터 전달 단절 의심"
                )
            elif _looks_like_refusal(summ):
                issues.append(
                    f"{fn}: 요약 LLM이 본문을 요구하며 거부함 — 헤드라인 기반 요약 프롬프트 필요"
                )
            else:
                produced_content = True

    if saw_fetch and not fetched_something:
        issues.append("어떤 fetch 단계도 콘텐츠를 가져오지 못함 (소스 전부 실패)")
    if saw_process and not produced_content:
        issues.append("요약 단계가 본문을 전혀 생성하지 못함 (빈 메일 발송 위험)")

    return {
        "healthy": not issues,
        "issues": issues,
        "fetched_something": fetched_something,
        "produced_content": produced_content,
    }


def _format_error_reason(result: dict[str, Any]) -> str:
    """execute_tool의 에러 결과를 '어디서 틀렸는지' 한 줄로 정리한다."""
    err_type = result.get("error_type")
    err_msg = result.get("error_message")
    line = result.get("line")
    code = result.get("code")

    if err_type or err_msg:
        parts = []
        if line:
            parts.append(f"tool.py {line}번째 줄")
        if err_type:
            parts.append(f"{err_type}: {err_msg or ''}".strip())
        else:
            parts.append(str(err_msg))
        reason = " — ".join(parts)
        if code:
            reason += f"  ↳ `{code}`"
        return reason[:400]

    if result.get("status") == "timeout":
        return result.get("error") or "실행 시간 초과"

    err = result.get("error") or result.get("stderr") or "도구 실행 오류"
    return str(err)[:400]


FAILURE_STATUSES = {"blocked", "error", "timeout", "failed", "fail"}

_FETCH_KEYWORDS = ("fetch", "scrape", "crawl", "download")


def _diagnose_step(func_name: str, inner: Any) -> tuple[bool, str]:
    """도구가 정상 종료했더라도 실질적으로 실패했는지 진단한다.

    반환: (정상 여부, 실패 사유)
    """
    if not isinstance(inner, dict):
        return True, ""

    status = str(inner.get("status", "")).lower()
    if status in FAILURE_STATUSES:
        reasons = {
            "blocked": "대상 사이트가 스크래핑을 차단했습니다 (robots.txt 등)",
            "timeout": "대상 사이트 응답 시간 초과",
            "error": "도구 실행 중 오류 발생",
            "failed": "도구 실행 실패",
            "fail": "도구 실행 실패",
        }
        base = reasons.get(status, f"실패 상태: {status}")
        # 도구가 자체적으로 남긴 구체적 메시지를 우선 노출한다.
        detail = (
            inner.get("message")
            or inner.get("error_message")
            or inner.get("error")
            or inner.get("msg")
            or inner.get("reason")
            or inner.get("detail")
        )
        if detail:
            return False, f"{base} — {str(detail)[:300]}"
        return False, base

    fn = func_name.lower()
    if any(k in fn for k in _FETCH_KEYWORDS):
        content = inner.get("content") or inner.get("html") or inner.get("text")
        articles = inner.get("articles")
        if not content and not articles:
            return False, "콘텐츠를 가져오지 못했습니다 (본문 없음)"

    return True, ""


_CARRY_KEYS = (
    "content", "summary", "summary_text", "articles",
    "html", "html_content", "text", "body", "digest", "output",
)


def _accumulate_carry(carry: dict[str, Any], inner: Any) -> None:
    """도구 출력에서 의미 있는 값(본문/요약 등)을 누적 보존한다.

    발송 도구처럼 본문/요약을 안 돌려주는 단계가 끼어도, 직전까지의
    본문/요약이 사라지지 않아 뒤따르는 도구가 계속 사용할 수 있다.
    """
    if not isinstance(inner, dict):
        return
    for key in _CARRY_KEYS:
        value = inner.get(key)
        if value:  # truthy일 때만 갱신 (빈 값으로 덮어쓰지 않음)
            carry[key] = value


_MAX_PIPE_CHARS = 50_000


def _truncate(value: Any, limit: int = _MAX_PIPE_CHARS) -> Any:
    """파이프라인으로 전달되는 텍스트가 과도하게 크면 잘라낸다."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "\n…[truncated]"
    return value


def _build_context_from_prev(prev_output: Any) -> dict[str, Any]:
    """이전 도구 출력을 다양한 인자 이름(alias)으로 매핑한 context를 만든다.

    도구 함수의 파라미터 이름이 제각각이어도(content_text, html_content,
    summary_text 등) 시그니처 바인딩에서 매칭되도록 별칭을 모두 넣는다.
    값이 없으면 빈 문자열을 넣어 필수 인자 누락 에러를 막는다.
    """
    if prev_output is None:
        prev_output = {}
    if not isinstance(prev_output, dict):
        prev_output = {"output": str(prev_output)}

    # 구조화된 기사 목록은 별도 키로 그대로 전달한다 (summarize 도구가 articles를 읽음).
    articles = prev_output.get("articles")
    if not isinstance(articles, list):
        articles = []

    content = (
        prev_output.get("content")
        or prev_output.get("html")
        or prev_output.get("html_content")
        or prev_output.get("text")
        or prev_output.get("body")
        or prev_output.get("output")
        or _content_from_articles(articles)
        or ""
    )
    summary = (
        prev_output.get("summary")
        or prev_output.get("summary_text")
        or prev_output.get("digest")
        or prev_output.get("output")
        or content
        or ""
    )

    # 방어 장치: 도구가 원본 HTML을 그대로 반환해도 과도한 페이로드를 막는다.
    content = _truncate(content)
    summary = _truncate(summary)

    context: dict[str, Any] = {
        # 본문/콘텐츠 계열 별칭
        "content": content,
        "content_text": content,
        "html": content,
        "html_content": content,
        "text": content,
        "body": content,
        "raw_content": content,
        "article_text": content,
        # 요약/메일 본문 계열 별칭
        "summary": summary,
        "summary_text": summary,
        "digest": summary,
        "message": summary,
        "body_text": summary,
        # 구조화된 기사 목록 (요약 도구 입력)
        "articles": articles,
        "items": articles,
        "news": articles,
    }
    return context


def _content_from_articles(articles: list[Any]) -> str:
    """기사 목록에서 사람이 읽을 수 있는 본문 텍스트를 만든다.

    summarize 도구가 content만 읽는 경우에도 동작하도록 articles를 펼친다.
    """
    lines: list[str] = []
    for a in articles[:20]:
        if isinstance(a, dict):
            title = str(a.get("title", "")).strip()
            desc = str(a.get("summary", a.get("description", ""))).strip()
            if title and desc:
                lines.append(f"{title} - {desc}")
            elif title:
                lines.append(title)
        elif a:
            lines.append(str(a))
    return "\n".join(lines)
