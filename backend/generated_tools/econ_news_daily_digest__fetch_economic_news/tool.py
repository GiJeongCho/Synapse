import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

def fetch_economic_news(**kwargs):
    """
    Fetch latest economic news from multiple sources with fallback.
    Returns articles from the first successful source.
    """
    # Multiple news sources: RSS feeds and web scraping
    SOURCES = [
        "https://finance.yahoo.com/news/rssindex",
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.marketwatch.com/marketwatch/topstories"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    articles = []
    errors = []
    
    for source_url in SOURCES:
        try:
            response = httpx.get(
                source_url,
                timeout=15.0,
                headers=headers,
                follow_redirects=True
            )
            response.raise_for_status()
            
            # Parse RSS/Atom feed
            root = ET.fromstring(response.text)
            items = root.findall(".//item")
            
            if not items:
                items = root.findall(".//entry")  # Atom format
            
            for item in items[:10]:  # Limit to 10 articles
                title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or ""
                desc = item.findtext("description") or item.findtext("{http://www.w3.org/2005/Atom}summary") or ""
                link = item.findtext("link") or item.findtext("{http://www.w3.org/2005/Atom}link") or ""
                
                if isinstance(link, str) and link.startswith("http"):
                    pass
                elif hasattr(link, "get"):
                    link = link.get("href", "")
                
                title = title.strip()
                desc = desc.strip()[:300]
                link = link.strip() if isinstance(link, str) else ""
                
                if title:
                    articles.append({
                        "title": title,
                        "summary": desc,
                        "link": link,
                        "source": source_url.split("/")[2]
                    })
            
            if articles:
                break  # Success, stop trying other sources
        
        except Exception as e:
            errors.append(f"{source_url}: {str(e)}")
            continue
    
    if not articles:
        return {
            "status": "error",
            "content": "",
            "message": f"Failed to fetch from all sources: {'; '.join(errors)}"
        }
    
    # Format content for next stage
    content_text = "\n\n".join([
        f"[{a['source'].upper()}] {a['title']}\n{a['summary']}\nLink: {a['link']}"
        for a in articles
    ])[:15000]  # Truncate to 15000 chars
    
    return {
        "status": "success",
        "content": content_text,
        "articles": articles,
        "article_count": len(articles),
        "fetch_timestamp": datetime.now().isoformat()
    }