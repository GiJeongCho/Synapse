import os
import httpx
import json

def summarize_news(content="", articles=None, **kwargs):
    """Summarize news content using Anthropic Claude API"""
    try:
        # Build text from either content or articles
        text = content or ""
        if not text and articles:
            text = "\n\n".join(
                f"제목: {a.get('title', '')}\n요약: {a.get('summary', '')}\n출처: {a.get('source', '')}"
                for a in articles if isinstance(a, dict)
            )
        
        if not text:
            return {
                "status": "error",
                "summary": "",
                "message": "No content to summarize"
            }
        
        # Get API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # Fallback: create simple bullet summary without LLM
            if articles:
                summary = "🤖 오늘의 AI 뉴스 요약\n\n"
                for i, a in enumerate(articles[:6], 1):
                    summary += f"{i}. {a.get('title', '')}\n   {a.get('summary', '')[:150]}...\n\n"
                return {
                    "status": "success",
                    "summary": summary,
                    "content": text
                }
            return {
                "status": "error",
                "summary": "",
                "message": "ANTHROPIC_API_KEY not set and no articles for fallback"
            }
        
        # Call Anthropic API
        instruction = (
            "다음은 AI 관련 뉴스 헤드라인과 짧은 설명 목록입니다. "
            "본문 전문은 제공되지 않습니다. 주어진 제목과 설명만으로 "
            "한국어 불릿 요약(최대 6개 항목)을 작성하세요. "
            "각 항목은 핵심 내용을 간결하게 전달해야 합니다. "
            "추가 내용을 요청하거나 본문이 없다고 거부하지 말고, "
            "주어진 정보로 바로 요약하세요.\n\n"
            "형식:\n🤖 오늘의 AI 뉴스 요약\n\n• [항목1]\n• [항목2]\n...\n\n"
            f"뉴스 내용:\n{text[:8000]}"
        )
        
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
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
        result = resp.json()
        summary = result["content"][0]["text"]
        
        return {
            "status": "success",
            "summary": summary,
            "content": text
        }
        
    except Exception as e:
        # Fallback to simple summary on any error
        if articles:
            summary = "🤖 오늘의 AI 뉴스 (자동 요약)\n\n"
            for i, a in enumerate(articles[:6], 1):
                summary += f"{i}. {a.get('title', '')}\n\n"
            return {
                "status": "success",
                "summary": summary,
                "content": text,
                "message": f"LLM failed, used fallback: {str(e)}"
            }
        return {
            "status": "error",
            "summary": "",
            "message": f"Summarization error: {str(e)}"
        }
