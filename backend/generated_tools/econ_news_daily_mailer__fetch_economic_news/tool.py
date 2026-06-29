import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import hashlib
import json
import os
from datetime import datetime
import time

def fetch_economic_news(trigger_signal="", **kwargs):
    """
    Fetch economic news from multiple sources with fallback.
    Returns articles with deduplication by URL hash.
    """
    try:
        # Define multiple news sources (RSS feeds + web scraping)
        SOURCES = [
            {"type": "rss", "url": "https://finance.yahoo.com/news/rssindex"},
            {"type": "rss", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html"},
            {"type": "rss", "url": "https://feeds.bloomberg.com/markets/news.rss"},
            {"type": "rss", "url": "http://feeds.marketwatch.com/marketwatch/topstories"},
            {"type": "rss", "url": "https://feeds.reuters.com/reuters/businessNews"},
        ]
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        articles = []
        seen_urls = set()
        errors = []
        
        log_dir = os.getenv("LOG_DIR", "/tmp")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "econ-news-agent.log")
        
        for source in SOURCES:
            try:
                time.sleep(1)  # Rate limiting
                
                if source["type"] == "rss":
                    r = httpx.get(source["url"], timeout=15.0, headers=headers, follow_redirects=True)
                    r.raise_for_status()
                    root = ET.fromstring(r.text)
                    items = root.findall(".//item")[:10]
                    
                    for item in items:
                        title = (item.findtext("title") or "").strip()
                        desc = (item.findtext("description") or "").strip()
                        link = (item.findtext("link") or "").strip()
                        pub_date = (item.findtext("pubDate") or "").strip()
                        
                        # Deduplication by URL hash
                        url_hash = hashlib.md5(link.encode()).hexdigest()
                        if link and url_hash not in seen_urls:
                            seen_urls.add(url_hash)
                            articles.append({
                                "title": title,
                                "summary": desc[:300],
                                "link": link,
                                "pub_date": pub_date,
                                "source": source["url"]
                            })
                    
                    if articles:
                        break
                        
            except Exception as e:
                errors.append(f"{source['url']}: {str(e)}")
                continue
        
        if not articles:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "function": "fetch_economic_news",
                "status": "error",
                "message": "All sources failed",
                "errors": errors
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            return {
                "status": "error",
                "content": "",
                "articles": [],
                "message": "Failed to fetch news from all sources: " + "; ".join(errors)
            }
        
        # Build content string
        content_lines = []
        for i, article in enumerate(articles[:10], 1):
            content_lines.append(f"{i}. {article['title']}\n{article['summary']}\nSource: {article['link']}\n")
        
        content = "\n".join(content_lines)[:15000]
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "function": "fetch_economic_news",
            "status": "success",
            "article_count": len(articles),
            "unique_urls": len(seen_urls)
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return {
            "status": "success",
            "content": content,
            "articles": articles[:10],
            "article_count": len(articles)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "content": "",
            "articles": [],
            "message": f"Fetch failed: {str(e)}"
        }
