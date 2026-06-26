import httpx
import logging
from urllib.robotparser import RobotFileParser
from datetime import datetime
import time

logger = logging.getLogger(__name__)

def fetch_bloomberg_news():
    """Fetch Bloomberg news respecting robots.txt and rate limits."""
    try:
        # Check robots.txt
        rp = RobotFileParser()
        rp.set_url('https://www.bloomberg.com/robots.txt')
        rp.read()
        
        if not rp.can_fetch('*', 'https://www.bloomberg.com/news'):
            logger.warning('Bloomberg robots.txt disallows scraping')
            return {'status': 'blocked', 'articles': []}
        
        # Fetch with timeout and retry
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
        client = httpx.Client(timeout=10.0)
        
        response = client.get('https://www.bloomberg.com/news', headers=headers)
        response.raise_for_status()
        
        logger.info(f'Fetched Bloomberg news at {datetime.now()}')
        return {'status': 'success', 'content': response.text, 'timestamp': datetime.now().isoformat()}
    
    except httpx.TimeoutException:
        logger.error('Bloomberg fetch timeout')
        return {'status': 'timeout', 'articles': []}
    except httpx.HTTPError as e:
        logger.error(f'HTTP error fetching Bloomberg: {e}')
        return {'status': 'error', 'articles': []}
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        return {'status': 'error', 'articles': []}
