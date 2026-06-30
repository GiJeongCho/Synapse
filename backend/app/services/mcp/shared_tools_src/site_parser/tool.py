"""공용 사이트 파서 도구 (영구 보존 — 에이전트 삭제와 무관).

universal_parser 라이브러리를 감싸 표준 MCP 도구로 노출한다.
- topic 만 주면: 언어 자동 감지 → Google News RSS 자동 탐색 → 기사 수집
- url 을 주면: 해당 페이지 본문을 추출

런타임이 shared_tools 디렉터리를 sys.path 에 넣어주므로 import 가 가능하다.
"""

from __future__ import annotations

from typing import Any

try:
    from universal_parser import fetch_news, parse_url
except Exception as exc:  # noqa: BLE001
    fetch_news = None  # type: ignore
    parse_url = None  # type: ignore
    _IMPORT_ERROR = str(exc)
else:
    _IMPORT_ERROR = ""


def site_parser(topic: str = "", url: str = "", limit: int = 10, **kwargs: Any) -> dict[str, Any]:
    """주제 또는 URL로 콘텐츠를 자동 수집·파싱한다.

    우선순위: url 이 있으면 해당 페이지 본문 추출, 없으면 topic 으로 뉴스 수집.
    반환: {status, articles, content, ...}
    """
    if fetch_news is None or parse_url is None:
        return {"status": "error", "content": "", "message": f"universal_parser import 실패: {_IMPORT_ERROR}"}

    topic = topic or kwargs.get("query") or kwargs.get("keyword") or ""
    url = url or kwargs.get("link") or ""

    if url:
        return parse_url(url)
    return fetch_news(topic=topic, limit=limit)
