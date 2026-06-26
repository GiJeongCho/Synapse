import httpx
import json
import os

def summarize_content(html_content):
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return {'status': 'error', 'summary': '', 'message': 'Missing ANTHROPIC_API_KEY'}
        
        if not html_content or len(html_content.strip()) < 10:
            return {'status': 'error', 'summary': '', 'message': 'Empty content'}
        
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        payload = {
            'model': 'claude-3-5-sonnet-20241022',
            'max_tokens': 500,
            'messages': [{
                'role': 'user',
                'content': f'Summarize these financial news headlines in 3-4 sentences:\n\n{html_content}'
            }]
        }
        
        resp = httpx.post('https://api.anthropic.com/v1/messages', json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            return {'status': 'error', 'summary': '', 'message': f'API error {resp.status_code}'}
        
        data = resp.json()
        summary = data.get('content', [{}])[0].get('text', '')
        return {'status': 'success', 'summary': summary}
    except Exception as e:
        return {'status': 'error', 'summary': '', 'message': str(e)}
