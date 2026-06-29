import httpx
import xml.etree.ElementTree as ET
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def naver_econ_news_fetcher(retries=3, timeout=15.0, **kwargs):
    """
    Fetch latest economic news from Naver News RSS feed.
    Respects robots.txt and implements retry logic with exponential backoff.
    Returns articles list and concatenated content string.
    """
    url = "https://news.naver.com/rss/economy.xml"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    articles = []
    last_error = None
    
    for attempt in range(retries):
        try:
            logger.info(f"Fetching Naver economic news (attempt {attempt + 1}/{retries})")
            response = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            items = root.findall(".//item")[:10]
            
            for item in items:
                title = (item.findtext("title") or "").strip()
                description = (item.findtext("description") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                
                if title:
                    articles.append({
                        "title": title,
                        "summary": description[:300] if description else "",
                        "link": link,
                        "pub_date": pub_date
                    })
            
            if articles:
                content = "\n".join(
                    f"{a['title']} - {a['summary']}" for a in articles
                )[:15000]
                logger.info(f"Successfully fetched {len(articles)} articles")
                return {
                    "status": "success",
                    "articles": articles,
                    "content": content,
                    "fetch_time": datetime.now().isoformat()
                }
            else:
                logger.warning("No articles found in RSS feed")
                return {
                    "status": "success",
                    "articles": [],
                    "content": "",
                    "fetch_time": datetime.now().isoformat()
                }
        
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}: {str(e)}"
            logger.warning(f"HTTP error on attempt {attempt + 1}: {last_error}")
            if attempt < retries - 1:
                import time
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        except ET.ParseError as e:
            last_error = f"XML parse error: {str(e)}"
            logger.error(f"Failed to parse RSS XML: {last_error}")
            break
        
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error(f"Error fetching news on attempt {attempt + 1}: {last_error}")
            if attempt < retries - 1:
                import time
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    logger.error(f"Failed to fetch news after {retries} attempts. Last error: {last_error}")
    return {
        "status": "error",
        "articles": [],
        "content": "",
        "message": last_error or "Failed to fetch Naver economic news",
        "fetch_time": datetime.now().isoformat()
    }