from bs4 import BeautifulSoup
import logging
from collections import Counter
import re

logger = logging.getLogger(__name__)

def summarize_content(html_content):
    """Extract and summarize news articles from HTML."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract article headlines and snippets
        articles = []
        for item in soup.find_all(['article', 'div'], class_=re.compile('story|article|news')):
            headline = item.find(['h2', 'h3', 'a'])
            snippet = item.find(['p', 'span'], class_=re.compile('summary|description'))
            
            if headline and snippet:
                articles.append({
                    'headline': headline.get_text(strip=True)[:100],
                    'snippet': snippet.get_text(strip=True)[:200]
                })
        
        # Create summary
        summary_text = '\n'.join([f"- {a['headline']}: {a['snippet']}" for a in articles[:5]])
        
        logger.info(f'Summarized {len(articles)} articles')
        return {'status': 'success', 'summary': summary_text, 'article_count': len(articles)}
    
    except Exception as e:
        logger.error(f'Summarization error: {e}')
        return {'status': 'error', 'summary': '', 'article_count': 0}
