import os
import httpx
from datetime import datetime

def summarize_news(content="", articles=None, **kwargs):
    """Summarize AI news into Korean digest"""
    text = content or ""
    
    if not text and articles:
        if isinstance(articles, list):
            text = "\n\n".join(
                f"{a.get('title', '')}\n{a.get('summary', '')}"
                for a in articles if isinstance(a, dict)
            )
    
    if not text:
        return {
            "status": "error",
            "summary": "",
            "message": "No content to summarize"
        }
    
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        simple_summary = f"""🤖 AI 뉴스 다이제스트 ({datetime.now().strftime('%Y-%m-%d')})

{text[:2000]}

※ 상세 요약을 위해 ANTHROPIC_API_KEY 설정이 필요합니다."""
        return {
            "status": "success",
            "summary": simple_summary,
            "content": simple_summary
        }
    
    try:
        instruction = (
            "다음은 AI 관련 뉴스 헤드라인과 짧은 설명 목록입니다. 본문 전문은 제공되지 않습니다. "
            "주어진 제목과 설명만으로 한국어 불릿 요약(최대 8개 항목)을 작성하세요. "
            "각 항목은 핵심 내용을 명확히 전달하되 간결하게 작성하세요. "
            "추가 내용을 요청하거나 본문이 없다고 거부하지 말고, 주어진 정보로 바로 요약하세요.\n\n"
            f"뉴스 내용:\n{text[:8000]}"
        )
        
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 800,
                "messages": [{"role": "user", "content": instruction}]
            },
            timeout=30.0
        )
        resp.raise_for_status()
        
        summary_text = resp.json()["content"][0]["text"]
        
        formatted = f"""🤖 AI 뉴스 다이제스트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})

{summary_text}

---
생성: AI News Curator Agent"""
        
        return {
            "status": "success",
            "summary": formatted,
            "content": formatted
        }
        
    except Exception as e:
        return {
            "status": "error",
            "summary": "",
            "message": f"Summarization failed: {str(e)}"
        }