import httpx
import time
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def fetch_yahoo_finance(max_retries=3, backoff_factor=2):
    url = 'https://finance.yahoo.com/news'
    robots_url = 'https://finance.yahoo.com/robots.txt'
    
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        if not rp.can_fetch('*', url):
            return {'status': 'error', 'message': 'robots.txt disallows scraping'}
        
        for attempt in range(max_retries):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; FinanceBot/1.0)'}
                response = httpx.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = []
                for item in soup.find_all('h3')[:10]:
                    link = item.find('a')
                    if link:
                        articles.append({
                            'title': link.get_text(strip=True),
                            'url': link.get('href', ''),
                            'timestamp': int(time.time())
                        })
                
                logger.info(f'Fetched {len(articles)} articles from Yahoo Finance')
                return {'status': 'success', 'articles': articles, 'content': str(articles)}
            except httpx.HTTPError as e:
                wait_time = backoff_factor ** attempt
                logger.warning(f'Attempt {attempt+1} failed: {e}. Retrying in {wait_time}s')
                time.sleep(wait_time)
        
        return {'status': 'error', 'message': 'Max retries exceeded'}
    except Exception as e:
        logger.error(f'Error fetching Yahoo Finance: {e}')
        return {'status': 'error', 'message': str(e)}
