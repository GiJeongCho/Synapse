import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

def fetch_economic_news(**kwargs):
    """Fetch economic news from multiple RSS sources with fallback."""
    SOURCES = [
        "https://finance.yahoo.com/news/rssindex",
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "http://feeds.marketwatch.com/marketwatch/topstories",
        "https://news.google.com/rss/search?q=economy&hl=en"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    articles = []
    errors = []
    
    for src in SOURCES:
        try:
            r = httpx.get(src, timeout=15.0, headers=headers, follow_redirects=True)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            items = root.findall(".//item")[:10]
            articles = [
                {
                    "title": (it.findtext("title") or "").strip(),
                    "summary": (it.findtext("description") or "").strip()[:300],
                    "link": (it.findtext("link") or "").strip(),
                    "pubDate": (it.findtext("pubDate") or "").strip()
                }
                for it in items if it.findtext("title")
            ]
            if articles:
                break
        except Exception as e:
            errors.append(f"{src}: {str(e)}")
    
    if not articles:
        return {"status": "error", "content": "", "message": "All sources failed: " + "; ".join(errors)}
    
    content = "\n".join([f"{a['title']} - {a['summary']}" for a in articles])[:15000]
    return {"status": "success", "articles": articles, "content": content}
