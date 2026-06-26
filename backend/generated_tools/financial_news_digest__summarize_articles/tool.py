import os
import httpx
import json

def summarize_articles(articles):
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return {'status': 'error', 'message': 'ANTHROPIC_API_KEY not set'}
        
        if not articles or len(articles) == 0:
            return {'status': 'success', 'summaries': []}
        
        article_text = '\n'.join([f"- {a.get('title', 'N/A')}" for a in articles[:5]])
        prompt = f"Summarize these financial news headlines in 2-3 sentences:\n{article_text}"
        
        payload = {
            'model': 'claude-3-5-sonnet-20241022',
            'max_tokens': 300,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        
        headers = {'x-api-key': api_key, 'content-type': 'application/json'}
        response = httpx.post('https://api.anthropic.com/v1/messages', json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        summary = result['content'][0]['text'] if result.get('content') else 'No summary generated'
        return {'status': 'success', 'summary': summary, 'article_count': len(articles)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
