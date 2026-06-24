"""Fetch 노드(§6) — 대상 URL에서 원본 콘텐츠를 가져온다."""
from __future__ import annotations

from typing import Any

import httpx
from langchain_core.runnables import RunnableConfig

from app.agents.crawl_agent.state import CrawlAgentState
from app.core.logging import logger

log = logger(__name__)

_REQUEST_TIMEOUT = 30.0


async def fetch_node(
    state: CrawlAgentState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """httpx를 사용하여 URL의 콘텐츠를 가져온다."""
    url = state["url"]

    log.info("fetch_node 시작: url=%s", url)

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        log.error("fetch_node HTTP 오류: status=%d, url=%s", exc.response.status_code, url)
        return {
            "error": f"HTTP {exc.response.status_code}: {url}",
            "metadata": {
                "status_code": exc.response.status_code,
                "content_type": exc.response.headers.get("content-type", ""),
                "url": str(exc.response.url),
            },
        }
    except httpx.RequestError as exc:
        log.error("fetch_node 요청 실패: %s, url=%s", exc, url)
        return {"error": f"Request failed: {exc}"}

    content_type = response.headers.get("content-type", "")
    raw_content = response.text

    log.info(
        "fetch_node 완료: status=%d, content_type=%s, length=%d",
        response.status_code,
        content_type,
        len(raw_content),
    )

    return {
        "raw_content": raw_content,
        "metadata": {
            "status_code": response.status_code,
            "content_type": content_type,
            "url": str(response.url),
        },
    }
