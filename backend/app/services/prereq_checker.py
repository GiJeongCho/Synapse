"""에이전트 실행 전 필수 요구사항 체크.

에이전트가 사용하는 도구를 분석하여 필요한 설정(SMTP, API 키 등)이
제대로 구성되어 있는지 사전 확인한다.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings

CAPABILITY_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "email": {
        "label": "이메일 발송 (SMTP)",
        "check": lambda: bool(settings.smtp_user and settings.smtp_password),
        "hint": ".env에 SMTP_USER, SMTP_PASSWORD 설정 필요 (네이버: IMAP/SMTP 사용 설정 + 앱 비밀번호)",
        "keywords": ["mail", "email", "smtp", "send_email", "메일"],
    },
    "llm": {
        "label": "LLM API 키",
        "check": lambda: bool(settings.anthropic_api_key or settings.openai_api_key),
        "hint": ".env에 ANTHROPIC_API_KEY 또는 OPENAI_API_KEY 설정 필요",
        "keywords": ["llm", "gpt", "claude", "anthropic", "openai"],
    },
    "embedding": {
        "label": "임베딩 API",
        "check": lambda: bool(settings.embed_api_url),
        "hint": ".env에 EMBED_API_URL 설정 필요",
        "keywords": ["embed", "vector", "similarity"],
    },
    "web_scraping": {
        "label": "웹 스크래핑 (httpx/bs4)",
        "check": lambda: True,
        "hint": "httpx, beautifulsoup4 패키지 필요 (pip install httpx beautifulsoup4)",
        "keywords": ["scrape", "crawl", "fetch", "bloomberg", "news", "web", "크롤"],
    },
}


def check_prerequisites(
    agent_spec: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None,
    user_request: str = "",
) -> list[dict[str, Any]]:
    """에이전트의 필수 요구사항을 점검한다.

    Returns:
        [{"capability": str, "label": str, "ok": bool, "hint": str}, ...]
    """
    search_text = user_request.lower()

    if agent_spec:
        caps = agent_spec.get("required_capabilities", [])
        search_text += " " + " ".join(str(c) for c in caps).lower()
        search_text += " " + str(agent_spec.get("persona", "")).lower()
        search_text += " " + str(agent_spec.get("goal", "")).lower()

    if tools:
        for t in tools:
            search_text += " " + t.get("tool_id", "").lower()
            search_text += " " + t.get("name", "").lower()
            search_text += " " + t.get("description", "").lower()
            for fn in t.get("functions", []):
                search_text += " " + fn.lower()

    results = []
    for cap_id, cap_info in CAPABILITY_REQUIREMENTS.items():
        matched = any(kw in search_text for kw in cap_info["keywords"])
        if matched:
            ok = cap_info["check"]()
            results.append({
                "capability": cap_id,
                "label": cap_info["label"],
                "ok": ok,
                "hint": "" if ok else cap_info["hint"],
            })

    if agent_spec and isinstance(agent_spec, dict):
        project_files = agent_spec.get("project_files", {})
        if isinstance(project_files, dict):
            required_env = project_files.get("required_env", [])
            if isinstance(required_env, list):
                import os
                for env_item in required_env:
                    if not isinstance(env_item, dict):
                        continue
                    name = env_item.get("name", "")
                    if not name:
                        continue
                    already = any(r["capability"] == f"env_{name}" for r in results)
                    if already:
                        continue
                    val = os.getenv(name, "") or getattr(settings, name.lower(), "")
                    results.append({
                        "capability": f"env_{name}",
                        "label": f"{name}: {env_item.get('description', '')}",
                        "ok": bool(val),
                        "hint": f".env에 {name} 설정 필요 (예: {env_item.get('example', '')})" if not val else "",
                    })

    return results
