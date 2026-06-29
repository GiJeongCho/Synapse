import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def fetch_economic_news(trigger_signal="", **kwargs):
    """
    Fetch latest economic news from multiple sources (RSS feeds + web scraping).
    Uses fallback strategy: tries each source in order until one succeeds.
    Returns articles and concatenated content (max 15000 chars).
    """
    # Multi-source fallback list: RSS feeds + scrape URLs
    SOURCES = [
        {"type": "rss", "url": "https://finance.yahoo.com/news/rssindex", "name": "Yahoo Finance"},
        {"type": "rss", "url": "https://feeds.bloomberg.com/markets/news.rss", "name": "Bloomberg Markets"},
        {"type": "rss", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html", "name": "CNBC Economy"},
        {"type": "rss", "url": "http://feeds.marketwatch.com/marketwatch/topstories", "name": "MarketWatch"},
        {"type": "rss", "url": "https://news.google.com/rss/search?q=economy&hl=en", "name": "Google News Economy"},
    ]
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    articles = []
    errors = []
    
    for source in SOURCES:
        try:
            logger.info(f"Attempting to fetch from {source['name']}...")
            r = httpx.get(source["url"], timeout=15.0, headers=headers, follow_redirects=True)
            r.raise_for_status()
            
            if source["type"] == "rss":
                root = ET.fromstring(r.text)
                items = root.findall(".//item")[:10]
                
                for item in items:
                    title = (item.findtext("title") or "").strip()
                    desc = (item.findtext("description") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    pub_date = (item.findtext("pubDate") or "").strip()
                    
                    if title:
                        articles.append({
                            "title": title,
                            "summary": desc[:300] if desc else "",
                            "link": link,
                            "source": source["name"],
                            "pub_date": pub_date
                        })
                
                if articles:
                    logger.info(f"Successfully fetched {len(articles)} articles from {source['name']}")
                    break
        except Exception as e:
            error_msg = f"{source['name']}: {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
            continue
    
    if not articles:
        error_summary = "; ".join(errors) if errors else "No sources available"
        logger.error(f"All sources failed: {error_summary}")
        return {
            "status": "error",
            "articles": [],
            "content": "",
            "message": f"Failed to fetch news from all sources: {error_summary}"
        }
    
    # Build concatenated content
    content_lines = []
    for article in articles:
        line = f"[{article['source']}] {article['title']}"
        if article['summary']:
            line += f" - {article['summary']}"
        content_lines.append(line)
    
    content = "\n\n".join(content_lines)[:15000]
    
    return {
        "status": "success",
        "articles": articles,
        "content": content,
        "article_count": len(articles),
        "message": f"Fetched {len(articles)} economic news articles"
    }
