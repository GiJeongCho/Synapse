import os
import httpx

def summarize_news_articles(content="", articles=None, **kwargs):
    """
    Summarize news articles using Anthropic Claude API.
    Handles both content string and articles list inputs.
    """
    # Build text to summarize
    text = content or ""
    if not text and articles:
        if isinstance(articles, list):
            text = "\n".join(
                f"{a.get('title', '')} - {a.get('summary', '')}"
                for a in articles if isinstance(a, dict)
            )
    
    if not text:
        return {
            "status": "error",
            "summary": "",
            "message": "No content or articles provided"
        }
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "summary": "",
            "message": "ANTHROPIC_API_KEY not set"
        }
    
    # Prepare prompt for Claude
    instruction = (
        "다음은 뉴스 헤드라인과 짧은 설명 목록입니다. 본문 전문은 제공되지 않습니다. "
        "주어진 제목과 설명만으로 한국어 불릿 요약(최대 8줄)을 작성하세요. "
        "추가 내용을 요청하거나 본문이 없다고 거부하지 말고, 주어진 정보로 바로 요약하세요.\n\n"
    )
    
    try:
        resp = httpx.post(
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
                    {"role": "user", "content": instruction + text}
                ]
            },
            timeout=30.0
        )
        resp.raise_for_status()
        result = resp.json()
        summary = result["content"][0]["text"]
        
        return {
            "status": "success",
            "summary": summary,
            "content": text
        }
    except Exception as e:
        return {
            "status": "error",
            "summary": "",
            "message": f"Claude API error: {str(e)}"
        }
