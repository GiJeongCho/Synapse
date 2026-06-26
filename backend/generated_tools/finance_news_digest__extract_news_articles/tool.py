from bs4 import BeautifulSoup
import re

def extract_news_articles(html_content, max_articles=10):
    """
    Extract news articles from Yahoo Finance HTML.
    Returns dict with status and articles list.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        articles = []
        
        # Find article containers
        article_elements = soup.find_all('a', {'data-test-id': 'internal-link'}, limit=max_articles)
        
        for elem in article_elements:
            try:
                title = elem.get_text(strip=True)
                link = elem.get('href', '')
                if title and link:
                    if not link.startswith('http'):
                        link = 'https://finance.yahoo.com' + link
                    articles.append({
                        'title': title,
                        'link': link,
                        'source': 'Yahoo Finance'
                    })
            except:
                continue
        
        return {
            'status': 'success',
            'articles': articles,
            'count': len(articles)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'articles': []}
