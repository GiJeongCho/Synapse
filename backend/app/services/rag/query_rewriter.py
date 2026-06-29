"""LLM 기반 쿼리 재작성 — 오타 교정 + 검색 최적화."""
from __future__ import annotations
import re
from anthropic import Anthropic
from app.core.config import settings


def _fallback_normalize(query: str) -> str:
    """LLM 실패 시 규칙 기반 폴백."""
    query = re.sub(r'제\s*(\d+)\s*조', r'제\1조', query)
    query = re.sub(r'\s+', ' ', query).strip()
    return query


async def rewrite_query(query: str) -> str:
    """LLM으로 쿼리 재작성. 실패 시 원본 반환."""
    if not settings.anthropic_api_key:
        return _fallback_normalize(query)

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=settings.llm_model,
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": (
                    "다음 검색 쿼리의 오타와 띄어쓰기를 교정하고, "
                    "문서 검색에 최적화된 형태로 간결하게 재작성해줘.\n"
                    "규칙:\n"
                    "- 핵심 키워드만 남겨\n"
                    "- 조문 번호는 붙여써 (제9조, 제12항)\n"
                    "- JSON으로만 응답: {\"query\": \"재작성된 쿼리\"}\n\n"
                    f"원본: {query}"
                ),
            }],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```\w*\n?", "", raw).strip()
        import json
        result = json.loads(raw)
        return result.get("query", query)
    except Exception:
        return _fallback_normalize(query)