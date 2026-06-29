import httpx
import hashlib
import time
import os
from datetime import datetime

def fetch_bloomberg_news(max_retries=3, **kwargs):
    """
    Fetch Bloomberg news from RSS feed with exponential backoff.
    Returns dict with status, content (list of articles), and content_hash for deduplication.
    """
    rss_url = "https://feeds.bloomberg.com/markets/news.rss"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for attempt in range(max_retries):
        try:
            response = httpx.get(rss_url, headers=headers, timeout=15.0)
            response.raise_for_status()
            
            # Parse RSS content
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.text)
            
            articles = []
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                desc = item.findtext("description", "")
                pub_date = item.findtext("pubDate", "")
                
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": desc[:500] if desc else "",
                        "pub_date": pub_date
                    })
            
            # Create content hash for deduplication
            content_str = "|".join([a["title"] + a["link"] for a in articles])
            content_hash = hashlib.md5(content_str.encode()).hexdigest()
            
            return {
                "status": "success",
                "content": articles,
                "content_hash": content_hash,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            wait_time = 2 ** attempt
            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            return {
                "status": "error",
                "content": [],
                "content_hash": "",
                "error": f"Failed to fetch Bloomberg news after {max_retries} attempts: {str(e)}"
            }
