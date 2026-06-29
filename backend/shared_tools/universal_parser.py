"""범용 사이트 파서 라이브러리 (공용·영구 보존).

주제(topic)만 주면 언어를 자동 감지해 Google News RSS를 만들어 기사를 수집하고,
임의 URL은 HTML 본문을 깔끔하게 추출한다. 생성된 에이전트 도구들이
``from universal_parser import fetch_news, parse_url`` 로 재사용한다.

의존성: stdlib + httpx + beautifulsoup4 (느슨하게 import — 없으면 기능 축소).
"""

from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any

try:
    import httpx
except Exception:  # noqa: BLE001
    httpx = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except Exception:  # noqa: BLE001
    BeautifulSoup = None  # type: ignore

_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Accept-Language": "ko,en;q=0.8"}

# 주제와 무관하게 동작하는, 검증된 키리스 폴백 피드 (영문 경제/일반).
_GENERIC_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.marketwatch.com/marketwatch/topstories",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
]


def _detect_lang(text: str) -> str:
    """텍스트에 한글이 있으면 'ko', 아니면 'en'."""
    return "ko" if re.search(r"[\uac00-\ud7a3]", text or "") else "en"


def google_news_rss(topic: str, lang: str = "auto") -> str:
    """주제로 Google News RSS 검색 URL을 만든다 (언어/국가 자동)."""
    if lang == "auto":
        lang = _detect_lang(topic)
    q = urllib.parse.quote(topic.strip() or ("경제" if lang == "ko" else "news"))
    if lang == "ko":
        return f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _get(url: str, timeout: float = 15.0) -> str | None:
    """URL을 GET 해 텍스트를 반환한다. 실패하면 None."""
    if httpx is None:
        return None
    try:
        r = httpx.get(url, timeout=timeout, headers=_HEADERS, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception:  # noqa: BLE001 — 폴백을 위해 조용히 실패
        return None


def _parse_rss(xml_text: str, limit: int) -> list[dict[str, str]]:
    """RSS/Atom XML에서 기사 목록을 추출한다."""
    articles: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return articles

    items = root.findall(".//item")
    if not items:  # Atom
        ns = {"a": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//a:entry", ns)

    for it in items[:limit]:
        title = (it.findtext("title") or "").strip()
        desc = it.findtext("description") or it.findtext("summary") or ""
        if not desc:
            for child in it:
                if child.tag.endswith("summary") or child.tag.endswith("content"):
                    desc = child.text or ""
                    break
        desc = _strip_html(desc).strip()[:500]
        link = (it.findtext("link") or "").strip()
        if not link:
            le = it.find("{http://www.w3.org/2005/Atom}link")
            if le is not None:
                link = le.get("href", "")
        if title:
            articles.append({"title": title, "summary": desc, "link": link})
    return articles


def _strip_html(text: str) -> str:
    """HTML 태그를 제거해 평문으로 만든다."""
    if not text:
        return ""
    if BeautifulSoup is not None:
        try:
            return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
        except Exception:  # noqa: BLE001
            pass
    return re.sub(r"<[^>]+>", " ", text)


def parse_url(url: str, max_chars: int = 15000) -> dict[str, Any]:
    """임의의 웹페이지에서 본문 텍스트를 추출한다 (사이트 파서)."""
    html = _get(url)
    if not html:
        return {"status": "error", "content": "", "message": f"가져오기 실패: {url}"}

    if BeautifulSoup is None:
        text = _strip_html(html)[:max_chars]
        return {"status": "success", "content": text, "url": url}

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    # 본문 후보: <article> → <main> → 가장 텍스트가 많은 <div> → body
    node = soup.find("article") or soup.find("main")
    if node is None:
        candidates = soup.find_all(["div", "section"])
        node = max(candidates, key=lambda n: len(n.get_text(" ", strip=True)), default=None)
    target = node or soup.body or soup
    text = re.sub(r"\n{3,}", "\n\n", target.get_text("\n", strip=True))[:max_chars]
    title = (soup.title.get_text(strip=True) if soup.title else "")
    return {"status": "success", "title": title, "content": text, "url": url}


def fetch_news(
    topic: str = "",
    urls: list[str] | None = None,
    lang: str = "auto",
    limit: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """주제/소스로 뉴스 기사를 자동 수집한다.

    1) urls가 주어지면 그 RSS/페이지를 먼저 시도
    2) topic으로 Google News RSS(언어 자동)를 만들어 시도
    3) 검증된 일반 피드들로 폴백
    각 소스를 순서대로 시도해 첫 성공 결과를 반환한다.
    """
    topic = topic or kwargs.get("query") or kwargs.get("keyword") or ""
    sources: list[str] = []
    if urls:
        sources.extend([u for u in urls if isinstance(u, str) and u.startswith("http")])
    if topic:
        sources.append(google_news_rss(topic, lang))
    # 중복 호스트 제거 + 일반 폴백 추가
    seen_hosts: set[str] = set()
    deduped: list[str] = []
    for u in sources + _GENERIC_FEEDS:
        host = urllib.parse.urlparse(u).netloc
        if host and host not in seen_hosts:
            seen_hosts.add(host)
            deduped.append(u)

    errors: list[str] = []
    for src in deduped:
        xml_text = _get(src)
        if not xml_text:
            errors.append(f"{src}: 응답 없음/DNS 실패")
            continue
        articles = _parse_rss(xml_text, limit)
        if articles:
            content = "\n".join(
                f"{a['title']} - {a['summary']}" for a in articles
            )[:15000]
            return {
                "status": "success",
                "source": src,
                "articles": articles,
                "content": content,
                "count": len(articles),
            }
        # RSS가 아니면 일반 페이지로 간주해 본문 파싱 시도
        parsed = parse_url(src)
        if parsed.get("status") == "success" and parsed.get("content"):
            return {
                "status": "success",
                "source": src,
                "articles": [{"title": parsed.get("title", ""), "summary": "", "link": src}],
                "content": parsed["content"],
                "count": 1,
            }
        errors.append(f"{src}: 콘텐츠 없음")

    return {
        "status": "error",
        "articles": [],
        "content": "",
        "message": "모든 소스 실패: " + "; ".join(errors)[:500],
    }
