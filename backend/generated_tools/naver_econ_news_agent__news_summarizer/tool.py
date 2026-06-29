import httpx
import os
import logging
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def news_summarizer(content="", articles=None, **kwargs):
    """
    Summarize articles using Claude API.
    Handles both content string and articles list.
    Returns concise bullet-point summary focusing on economic impact.
    """
    try:
        # Get API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error('ANTHROPIC_API_KEY not set')
            return {
                'status': 'error',
                'summary': '',
                'content': '',
                'message': 'ANTHROPIC_API_KEY environment variable not configured'
            }
        
        # Build text to summarize
        text = content or ""
        if not text and articles:
            if isinstance(articles, list):
                text = "\n".join(
                    f"제목: {a.get('title', '')}\n설명: {a.get('summary', '')}"
                    for a in articles if isinstance(a, dict)
                )
        
        if not text:
            logger.warning('No content to summarize')
            return {
                'status': 'success',
                'summary': '요약할 기사가 없습니다.',
                'content': ''
            }
        
        # Prepare prompt for Claude
        instruction = (
            "다음은 뉴스 헤드라인과 짧은 설명 목록입니다. 본문 전문은 제공되지 않습니다. "
            "주어진 제목과 설명만으로 한국어 불릿 요약(최대 8줄)을 작성하세요. "
            "각 기사의 경제적 영향과 핵심 내용에 집중하세요. "
            "추가 내용을 요청하거나 본문이 없다고 거부하지 말고, 주어진 정보로 바로 요약하세요.\n\n"
        )
        
        # Call Claude API
        client = httpx.Client(timeout=30.0)
        response = client.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 800,
                'messages': [
                    {
                        'role': 'user',
                        'content': instruction + text[:5000]  # Truncate input
                    }
                ]
            }
        )
        
        if response.status_code != 200:
            error_msg = f"Claude API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'summary': '',
                'content': '',
                'message': error_msg
            }
        
        result = response.json()
        summary = result['content'][0]['text']
        
        client.close()
        
        logger.info(f"Summary generated: {len(summary)} characters")
        return {
            'status': 'success',
            'summary': summary,
            'content': summary
        }
    
    except Exception as e:
        logger.error(f"Summarization error: {str(e)}")
        return {
            'status': 'error',
            'summary': '',
            'content': '',
            'message': f"Summarization failed: {str(e)}"
        }
