"""Provisioner 노드(§6) — 실행 가능한 MCP 도구 Python 코드를 생성하고 저장한다."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.meta_agent.harness import ainvoke_json
from app.agents.meta_agent.prompts import PROVISIONER_PROMPT
from app.agents.meta_agent.state import MetaAgentState
from app.core.llm.adapter import get_llm_for_agent
from app.core.logging import logger
from app.services.mcp.tool_runtime import delete_tools_for_agent, save_tool

log = logger(__name__)

# 단계별 키워드 — 같은 단계의 중복 도구를 1개만 유지하기 위함
_STAGE_KEYWORDS = [
    ("fetch", ("fetch", "scrape", "crawl", "download")),
    ("check", ("check", "freshness", "dedup", "validate", "filter")),
    ("summarize", ("summarize", "extract", "parse", "analyze", "digest")),
    ("email", ("send", "email", "mail", "notify", "post")),
    ("schedule", ("schedule", "cron", "timer")),
]


def _classify_stage(tool: dict[str, Any]) -> str:
    """도구를 파이프라인 단계로 분류한다 (매칭 없으면 'other')."""
    name = str(tool.get("tool_id", "")).lower()
    for fn in tool.get("functions", []) or []:
        name += " " + str(fn).lower()
    for stage, kws in _STAGE_KEYWORDS:
        if any(kw in name for kw in kws):
            return stage
    return "other"


def _make_shared_fetch_tool(topic: str) -> dict[str, Any]:
    """공용 site_parser(universal_parser)를 호출하는 결정적 fetch 도구를 만든다.

    LLM이 만든 깨지기 쉬운 스크레이퍼 대신 검증된 공용 파서를 쓰게 해
    404·타임아웃·DNS 실패를 원천 차단한다.
    """
    code = (
        "def fetch_news(topic=" + repr(topic) + ", **kwargs):\n"
        "    try:\n"
        "        from universal_parser import fetch_news as _fetch\n"
        "    except Exception as e:\n"
        "        return {\"status\": \"error\", \"content\": \"\",\n"
        "                \"message\": \"universal_parser import 실패: \" + str(e)}\n"
        "    t = kwargs.get(\"topic\") or topic or \"\"\n"
        "    return _fetch(topic=t, limit=10)\n"
    )
    return {
        "tool_id": "fetch_news",
        "name": "뉴스/웹 수집 (공용 파서)",
        "description": "주제로 Google News RSS 등 검증된 소스를 자동 탐색해 기사를 수집",
        "code": code,
        "functions": ["fetch_news"],
    }


def _fetch_uses_shared(tool: dict[str, Any]) -> bool:
    """fetch 도구가 공용 라이브러리(universal_parser)를 사용하는지 검사한다."""
    return "universal_parser" in str(tool.get("code", ""))


def _ensure_shared_fetch(
    tools: list[dict[str, Any]], topic: str
) -> list[dict[str, Any]]:
    """fetch 단계를 공용 파서로 보장한다 ('both' 정책).

    - 이미 universal_parser를 쓰는 fetch가 있으면 그대로 둔다(특수 소스 LLM 허용).
    - 그렇지 않으면 깨지기 쉬운 fetch를 제거하고 공용 파서 fetch를 주입한다.
    """
    fetch_tools = [t for t in tools if _classify_stage(t) == "fetch"]
    if fetch_tools and any(_fetch_uses_shared(t) for t in fetch_tools):
        return tools  # LLM이 공용 파서 기반 fetch를 만들었으면 존중

    non_fetch = [t for t in tools if _classify_stage(t) != "fetch"]
    injected = _make_shared_fetch_tool(topic)
    if fetch_tools:
        log.info("깨지기 쉬운 fetch 도구를 공용 파서로 교체: %d개 제거", len(fetch_tools))
    else:
        log.info("fetch 도구가 없어 공용 파서 fetch 주입")
    return [injected] + non_fetch


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _extract_recipient(*texts: str) -> str:
    """요청/스펙 텍스트에서 수신자 이메일 주소를 추출한다 (첫 매칭)."""
    for t in texts:
        if not t:
            continue
        m = _EMAIL_RE.search(t)
        if m:
            return m.group(0)
    return ""


def _make_email_tool(recipient: str, subject: str) -> dict[str, Any]:
    """검증된 표준 SMTP 발송 도구를 만든다 (LLM이 메일 도구를 빠뜨렸을 때 주입).

    요약/본문 별칭(summary/summary_text/content/digest)을 모두 받아들이고,
    수신자는 kwargs > RECIPIENT_EMAIL 환경변수 > 주입된 기본값 순으로 결정한다.
    """
    code = (
        "import os, smtplib\n"
        "from email.mime.text import MIMEText\n"
        "from email.mime.multipart import MIMEMultipart\n"
        "\n"
        "def send_email(summary=\"\", summary_text=\"\", content=\"\", **kwargs):\n"
        "    body = summary or summary_text or content or kwargs.get(\"digest\") or \"\"\n"
        "    if not body:\n"
        "        return {\"status\": \"error\", \"message\": \"No content to send\"}\n"
        "    host = os.getenv(\"SMTP_HOST\", \"smtp.gmail.com\")\n"
        "    port = int(os.getenv(\"SMTP_PORT\", \"587\"))\n"
        "    user = os.getenv(\"SMTP_USER\", \"\")\n"
        "    pw = os.getenv(\"SMTP_PASSWORD\", \"\")\n"
        "    sender = os.getenv(\"SMTP_FROM\", user)\n"
        "    recipient = kwargs.get(\"recipient\") or os.getenv(\"RECIPIENT_EMAIL\") or "
        + repr(recipient) + "\n"
        "    if not user or not pw:\n"
        "        return {\"status\": \"error\", \"message\": \"SMTP credentials not configured\"}\n"
        "    if not recipient:\n"
        "        return {\"status\": \"error\", \"message\": \"No recipient configured\"}\n"
        "    msg = MIMEMultipart()\n"
        "    msg[\"From\"] = sender\n"
        "    msg[\"To\"] = recipient\n"
        "    msg[\"Subject\"] = " + repr(subject) + "\n"
        "    msg.attach(MIMEText(body, \"plain\"))\n"
        "    try:\n"
        "        if port == 465:\n"
        "            server = smtplib.SMTP_SSL(host, port, timeout=20)\n"
        "        else:\n"
        "            server = smtplib.SMTP(host, port, timeout=20)\n"
        "            server.starttls()\n"
        "        server.login(user, pw)\n"
        "        server.send_message(msg)\n"
        "        server.quit()\n"
        "    except Exception as e:\n"
        "        return {\"status\": \"error\", \"message\": \"Email send failed: \" + str(e)}\n"
        "    return {\"status\": \"success\", \"message\": \"Email sent to \" + recipient}\n"
    )
    return {
        "tool_id": "send_email",
        "name": "이메일 발송 (표준 SMTP)",
        "description": f"요약 결과를 {recipient or '설정된 수신자'}에게 메일로 발송",
        "code": code,
        "functions": ["send_email"],
    }


def _delivery_required(plan: dict[str, Any], spec_text: str) -> bool:
    """발송(메일) 단계가 필요한 요청인지 판정한다 (계획 컴포넌트 + 키워드)."""
    for comp in plan.get("architecture", {}).get("components", []) or []:
        if isinstance(comp, dict) and str(comp.get("stage", "")).lower() in ("deliver", "email"):
            return True
    return any(
        kw in spec_text
        for kw in ("email", "mail", "메일", "발송", "notify", "알림", "send")
    )


def _ensure_delivery(
    tools: list[dict[str, Any]],
    plan: dict[str, Any],
    spec_text: str,
    recipient: str,
    subject: str,
) -> list[dict[str, Any]]:
    """발송이 필요한데 메일 도구가 없으면 표준 SMTP 도구를 결정적으로 주입한다."""
    if any(_classify_stage(t) == "email" for t in tools):
        return tools
    if not _delivery_required(plan, spec_text):
        return tools
    log.info("발송 단계 누락 → 표준 이메일 도구 주입 (recipient=%s)", recipient or "미지정")
    return tools + [_make_email_tool(recipient, subject)]


def _dedupe_tools_by_stage(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """같은 단계(fetch/summarize/email/schedule 등)의 중복 도구를 1개만 남긴다.

    LLM이 minimal 규칙을 어겨도 결정적으로 도구 집합을 정리한다.
    'other' 단계는 모두 유지한다.
    """
    kept: list[dict[str, Any]] = []
    seen_stages: set[str] = set()
    dropped = 0
    for tool in tools:
        stage = _classify_stage(tool)
        if stage != "other" and stage in seen_stages:
            dropped += 1
            continue
        seen_stages.add(stage)
        kept.append(tool)
    if dropped:
        log.info("중복 도구 %d개 제거 (단계별 1개 유지)", dropped)
    return kept


async def provisioner(
    state: MetaAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """agent_spec + mcp_tools → system_prompt + 실행 가능한 도구 파일 생성."""
    agent_spec = state["agent_spec"]
    mcp_tools = state.get("mcp_tools", [])
    plan = state.get("plan", {})
    feedback = state.get("test_result", {}).get("suggestions", [])

    log.info("Provisioner 시작: %s", agent_spec.get("persona", "?")[:40])

    llm = get_llm_for_agent("meta")

    feedback_str = json.dumps(feedback, ensure_ascii=False) if feedback else "None"
    tools_summary = json.dumps(
        [{"name": t.get("name"), "capabilities": t.get("capabilities")} for t in mcp_tools[:5]],
        ensure_ascii=False,
    )

    messages = PROVISIONER_PROMPT.format_messages(
        agent_spec=json.dumps(agent_spec, ensure_ascii=False, indent=2),
        plan=json.dumps(plan, ensure_ascii=False, indent=2) if plan else "None",
        mcp_tools=tools_summary,
        feedback=feedback_str,
    )
    result = await ainvoke_json(
        llm, messages, node="provisioner", retries=2,
        fallback={"tools": [], "system_prompt": "", "workflow": []},
    )

    system_prompt = result.get("system_prompt", "")
    agent_id = result.get("agent_id", "agent_" + state.get("job_id", "unknown")[:8])
    tools = _dedupe_tools_by_stage(result.get("tools", []))
    workflow = result.get("workflow", [])

    # fetch 단계를 공용 파서로 보장한다 ('both' 정책: 공용 라이브러리 기반이면 LLM 작성 존중).
    fetch_topic = (
        plan.get("fetch_topic")
        or agent_spec.get("goal")
        or agent_spec.get("persona")
        or ""
    )[:80]
    tools = _ensure_shared_fetch(tools, fetch_topic)

    # 발송이 필요한 요청인데 메일 도구가 빠졌으면 표준 SMTP 도구를 결정적으로 주입한다.
    # (fetch와 동일한 '누락 보장' 정책 — Solo 모드에서도 발송 단계가 사라지지 않게)
    user_request = state.get("user_request", "")
    spec_text = (
        user_request + " "
        + json.dumps(agent_spec, ensure_ascii=False)
        + " " + json.dumps(workflow, ensure_ascii=False)
    ).lower()
    recipient = _extract_recipient(
        user_request, json.dumps(agent_spec, ensure_ascii=False)
    )
    subject = str(agent_spec.get("persona") or agent_spec.get("goal") or "Daily Summary")[:60]
    tools = _ensure_delivery(tools, plan, spec_text, recipient, subject)

    # 같은 agent_id로 이전에 저장된 도구를 먼저 정리한다.
    # (Dual 라운드 재생성·동일 이름 재생성 시 도구가 누적되는 것을 방지)
    removed = delete_tools_for_agent(agent_id)
    if removed:
        log.info("기존 도구 %d개 정리 후 재생성: agent_id=%s", removed, agent_id)

    saved_tools = []
    for tool in tools:
        tool_id = tool.get("tool_id", "")
        code = tool.get("code", "")
        if not tool_id or not code:
            continue

        full_tool_id = f"{agent_id}__{tool_id}"
        save_tool(full_tool_id, code, metadata={
            "agent_id": agent_id,
            "name": tool.get("name", tool_id),
            "description": tool.get("description", ""),
            "functions": tool.get("functions", [tool_id]),
        })
        saved_tools.append({
            "tool_id": full_tool_id,
            "name": tool.get("name", tool_id),
            "functions": tool.get("functions", [tool_id]),
        })

    required_env = result.get("required_env", [])

    project_files = {
        "tools": saved_tools,
        "workflow": workflow,
        "agent_id": agent_id,
        "required_env": required_env,
        "plan": plan,
    }

    log.info(
        "Provisioner 완료: agent_id=%s, %d개 도구 저장",
        agent_id, len(saved_tools),
    )

    return {
        "system_prompt": system_prompt,
        "project_files": project_files,
        "current_step": "provisioner",
    }
