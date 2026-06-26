import httpx
import time
from bs4 import BeautifulSoup

def fetch_yahoo_finance_news(max_retries=3, backoff_factor=2):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    url = 'https://finance.yahoo.com/news/'
    
    for attempt in range(max_retries):
        try:
            time.sleep(2)  # Respect rate limits
            response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.find_all('h3', limit=5)
                news_items = []
                for article in articles:
                    text = article.get_text(strip=True)
                    if text:
                        news_items.append(text)
                if news_items:
                    return {'status': 'success', 'content': ' | '.join(news_items), 'count': len(news_items)}
            return {'status': 'failed', 'content': '', 'http_code': response.status_code}
        except httpx.TimeoutException:
            wait_time = backoff_factor ** attempt
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                return {'status': 'timeout', 'content': '', 'message': 'Max retries exceeded'}
        except Exception as e:
            return {'status': 'error', 'content': '', 'message': str(e)}
    return {'status': 'failed', 'content': ''}
