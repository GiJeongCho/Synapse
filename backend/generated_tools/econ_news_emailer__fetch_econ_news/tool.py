import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

def fetch_econ_news(**kwargs):
    """
    Fetch economic news from multiple RSS feeds.
    Returns list of articles with title, summary, and link.
    """
    feeds = [
        "https://finance.yahoo.com/news/rssindex",
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "https://feeds.reuters.com/reuters/businessNews"
    ]
    
    articles = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        for feed_url in feeds:
            try:
                r = httpx.get(feed_url, timeout=15.0, headers=headers)
                r.raise_for_status()
                root = ET.fromstring(r.text)
                items = root.findall(".//item")[:5]
                
                for item in items:
                    title = (item.findtext("title") or "").strip()
                    desc = (item.findtext("description") or "").strip()[:300]
                    link = (item.findtext("link") or "").strip()
                    if title:
                        articles.append({"title": title, "summary": desc, "link": link})
            except Exception as e:
                continue
        
        if not articles:
            return {"status": "error", "content": "", "message": "No articles fetched from feeds"}
        
        articles = articles[:10]
        content = "\n\n".join([f"[{a['title']}]\n{a['summary']}\n{a['link']}" for a in articles])
        return {"status": "success", "content": content, "articles": articles}
    except Exception as e:
        return {"status": "error", "content": "", "message": str(e)}
