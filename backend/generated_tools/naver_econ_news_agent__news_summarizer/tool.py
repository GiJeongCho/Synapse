import os
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def news_summarizer(content="", articles=None, summary="", **kwargs):
    """
    Summarize economic news articles using Claude API.
    Handles both content string and articles list inputs.
    Returns concise bullet-point summary in Korean.
    """
    # Build text to summarize
    text = content or ""
    if not text and articles:
        text = "\n".join(
            (a.get("title", "") + " - " + a.get("summary", ""))
            for a in articles if isinstance(a, dict)
        )
    
    if not text:
        logger.warning("No content or articles provided for summarization")
        return {
            "status": "success",
            "summary": "요약할 뉴스 기사가 없습니다.",
            "content": "",
            "summary_time": datetime.now().isoformat()
        }
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        return {
            "status": "error",
            "summary": "",
            "message": "ANTHROPIC_API_KEY not configured",
            "summary_time": datetime.now().isoformat()
        }
    
    try:
        logger.info("Calling Claude API for news summarization")
        
        instruction = (
            "다음은 경제 뉴스 헤드라인과 짧은 설명 목록입니다. 본문 전문은 제공되지 않습니다. "
            "주어진 제목과 설명만으로 한국어 불릿 요약(최대 8줄)을 작성하세요. "
            "각 항목은 '• ' 로 시작하세요. "
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
                "max_tokens": 800,
                "messages": [
                    {"role": "user", "content": instruction + text[:8000]}
                ]
            },
            timeout=30.0
        )
        
        response.raise_for_status()
        result = response.json()
        
        if "content" in result and len(result["content"]) > 0:
            summary_text = result["content"][0].get("text", "")
            logger.info("Successfully generated summary")
            return {
                "status": "success",
                "summary": summary_text,
                "content": text[:5000],
                "summary_time": datetime.now().isoformat()
            }
        else:
            logger.error("Unexpected Claude API response format")
            return {
                "status": "error",
                "summary": "",
                "message": "Claude API returned unexpected format",
                "summary_time": datetime.now().isoformat()
            }
    
    except httpx.HTTPStatusError as e:
        error_msg = f"Claude API HTTP {e.response.status_code}: {e.response.text[:200]}"
        logger.error(error_msg)
        return {
            "status": "error",
            "summary": "",
            "message": error_msg,
            "summary_time": datetime.now().isoformat()
        }
    
    except Exception as e:
        error_msg = f"Summarization failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "summary": "",
            "message": error_msg,
            "summary_time": datetime.now().isoformat()
        }