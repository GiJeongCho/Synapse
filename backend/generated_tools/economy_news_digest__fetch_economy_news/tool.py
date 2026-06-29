import httpx
import xml.etree.ElementTree as ET
import hashlib
import os
from datetime import datetime

def fetch_economy_news(**kwargs):
    """Fetch economy news from multiple RSS sources with deduplication."""
    SOURCES = [
        "https://finance.yahoo.com/news/rssindex",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.cnbc.com/cnbc/international",
        "http://feeds.marketwatch.com/marketwatch/topstories",
        "https://feeds.reuters.com/reuters/businessNews"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    articles = []
    seen_hashes = set()
    errors = []
    
    for src in SOURCES:
        try:
            r = httpx.get(src, timeout=15.0, headers=headers, follow_redirects=True)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            items = root.findall(".//item")[:10]
            for item in items:
                title = (item.findtext("title") or "").strip()
                desc = (item.findtext("description") or "").strip()[:300]
                link = (item.findtext("link") or "").strip()
                if not title:
                    continue
                title_hash = hashlib.md5(title.encode()).hexdigest()
                if title_hash not in seen_hashes:
                    seen_hashes.add(title_hash)
                    articles.append({"title": title, "summary": desc, "link": link, "source": src.split("/")[2]})
            if len(articles) >= 10:
                break
        except Exception as e:
            errors.append(f"{src}: {str(e)}")
    
    if not articles:
        return {"status": "error", "content": "", "message": f"All sources failed: {'; '.join(errors)}"}
    articles = articles[:10]
    content = "\n".join(f"{a['title']} ({a['source']})\n{a['summary']}\nLink: {a['link']}" for a in articles)[:15000]
    return {"status": "success", "articles": articles, "content": content, "count": len(articles)}
