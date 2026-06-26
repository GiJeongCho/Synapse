import httpx
import json
import os
import logging

logger = logging.getLogger(__name__)

def summarize_articles(articles):
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return {'status': 'error', 'message': 'ANTHROPIC_API_KEY not set'}
    
    if not articles:
        return {'status': 'success', 'summary': 'No new articles to summarize.'}
    
    try:
        article_text = '\n'.join([f"- {a.get('title', 'N/A')}" for a in articles[:10]])
        
        payload = {
            'model': 'claude-3-5-sonnet-20241022',
            'max_tokens': 500,
            'messages': [{
                'role': 'user',
                'content': f'Summarize these financial news headlines in 2-3 sentences:\n{article_text}'
            }]
        }
        
        headers = {'x-api-key': api_key, 'anthropic-version': '2023-06-01'}
        response = httpx.post(
            'https://api.anthropic.com/v1/messages',
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        summary = result['content'][0]['text']
        logger.info('Articles summarized successfully')
        return {'status': 'success', 'summary': summary}
    except Exception as e:
        logger.error(f'Summarization error: {e}')
        return {'status': 'error', 'message': str(e)}
