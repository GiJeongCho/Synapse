import os
import httpx
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def news_summarizer(content="", articles=None, **kwargs):
    """
    Summarize articles using Claude API (Korean language).
    Falls back to simple text extraction if API unavailable.
    Enforces 500-word limit.
    """
    try:
        # Build text from articles or content
        text = content or ""
        if not text and articles:
            if isinstance(articles, list):
                text = "\n".join(
                    f"제목: {a.get('title', '')}\n설명: {a.get('summary', '')}"
                    for a in articles
                    if isinstance(a, dict)
                )
        
        if not text:
            logger.warning("No content to summarize")
            return {
                "status": "error",
                "summary": "",
                "content": "",
                "message": "No articles or content provided"
            }
        
        # Try Claude API summarization
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if api_key:
            try:
                logger.info("Attempting Claude API summarization")
                
                instruction = (
                    "다음은 뉴스 헤드라인과 짧은 설명 목록입니다. 본문 전문은 제공되지 않습니다. "
                    "주어진 제목과 설명만으로 한국어 불릿 요약(최대 6줄)을 작성하세요. "
                    "추가 내용을 요청하거나 본문이 없다고 거부하지 말고, 주어진 정보로 바로 요약하세요.\n\n"
                )
                
                response = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 600,
                        "messages": [
                            {
                                "role": "user",
                                "content": instruction + text[:5000]
                            }
                        ]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result["content"][0]["text"]
                    logger.info("Claude summarization successful")
                    return {
                        "status": "success",
                        "summary": summary[:500],
                        "content": text[:15000],
                        "summary_method": "claude",
                        "summary_time": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"Claude API error: {response.status_code}")
                    raise Exception(f"API returned {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Claude API failed, using fallback: {str(e)}")
        else:
            logger.info("ANTHROPIC_API_KEY not set, using fallback summarization")
        
        # Fallback: simple text extraction from articles
        if articles and isinstance(articles, list):
            summary = "\n".join(
                f"• {a.get('title', '')}"
                for a in articles[:6]
                if isinstance(a, dict) and a.get('title')
            )
        else:
            # Extract first 500 chars as summary
            summary = text[:500]
        
        logger.info("Using fallback summarization")
        return {
            "status": "success",
            "summary": summary,
            "content": text[:15000],
            "summary_method": "fallback",
            "summary_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in summarizer: {str(e)}")
        return {
            "status": "error",
            "summary": "",
            "content": "",
            "message": f"Summarizer exception: {str(e)}"
        }