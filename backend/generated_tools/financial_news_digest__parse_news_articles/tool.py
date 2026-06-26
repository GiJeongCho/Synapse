from bs4 import BeautifulSoup
import re

def parse_news_articles(html_content, max_articles=10):
    """
    Parse HTML content and extract news articles.
    Returns dict with status and articles list.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        articles = []
        
        for item in soup.find_all('a', {'data-test-id': 'internal-link'})[:max_articles]:
            try:
                title = item.get_text(strip=True)
                link = item.get('href', '')
                if title and link and 'finance.yahoo.com' in link:
                    articles.append({
                        'title': title[:100],
                        'link': link if link.startswith('http') else f'https://finance.yahoo.com{link}'
                    })
            except:
                continue
        
        return {
            'status': 'success',
            'articles': articles[:max_articles],
            'count': len(articles)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'articles': []}
