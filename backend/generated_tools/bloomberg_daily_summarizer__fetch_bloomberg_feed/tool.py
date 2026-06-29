import httpx
import hashlib
from datetime import datetime
import os

def fetch_bloomberg_feed(feed_url="https://www.bloomberg.com/feed/podcast/etf-report.xml", recipient="", **kwargs):
    """
    Fetch Bloomberg RSS feed and deduplicate articles by content hash.
    Returns list of articles with title, summary, and link.
    """
    try:
        recipient = recipient or kwargs.get("recipient") or os.getenv("RECIPIENT_EMAIL", "wzxcv123@naver.com")
        feed_url = feed_url or os.getenv("BLOOMBERG_FEED_URL", "https://www.bloomberg.com/feed/podcast/etf-report.xml")
        
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        response = httpx.get(feed_url, headers=headers, timeout=15.0)
        response.raise_for_status()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        articles = []
        seen_hashes = set()
        
        for item in root.findall(".//item")[:10]:
            title_elem = item.find("title")
            desc_elem = item.find("description")
            link_elem = item.find("link")
            
            title = title_elem.text if title_elem is not None else ""
            desc = desc_elem.text if desc_elem is not None else ""
            link = link_elem.text if link_elem is not None else ""
            
            content_hash = hashlib.md5((title + desc).encode()).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                articles.append({
                    "title": title[:100],
                    "summary": desc[:300],
                    "link": link
                })
        
        return {
            "status": "success",
            "content": str(articles),
            "articles": articles,
            "recipient": recipient,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"status": "error", "content": f"Feed fetch failed: {str(e)}", "articles": []}
