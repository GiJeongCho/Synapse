import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

def fetch_econ_news(**kwargs):
    """
    Fetch economic news from multiple RSS sources with fallback.
    Returns list of articles with title, summary, and link.
    """
    sources = [
        "https://finance.yahoo.com/news/rssindex",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "http://feeds.marketwatch.com/marketwatch/topstories"
    ]
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    articles = []
    errors = []
    
    for src in sources:
        try:
            r = httpx.get(src, timeout=15.0, headers=headers, follow_redirects=True)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            items = root.findall(".//item")[:10]
            
            for item in items:
                title = (item.findtext("title") or "").strip()
                desc = (item.findtext("description") or "").strip()
                link = (item.findtext("link") or "").strip()
                if title:
                    articles.append({
                        "title": title,
                        "summary": desc[:300] if desc else "",
                        "link": link
                    })
            
            if articles:
                break
        except Exception as e:
            errors.append(f"{src}: {str(e)}")
    
    if not articles:
        return {
            "status": "error",
            "content": "",
            "message": "All news sources failed: " + "; ".join(errors)
        }
    
    content = "\n".join([f"{a['title']} - {a['summary']}" for a in articles])[:15000]
    return {
        "status": "success",
        "articles": articles,
        "content": content,
        "count": len(articles)
    }