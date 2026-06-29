import os
import httpx
from datetime import datetime

def summarize_news(content="", **kwargs):
    """
    Summarize economic news using Anthropic Claude API.
    Falls back to simple title-based summary if API unavailable.
    """
    text = content or kwargs.get("content") or ""
    
    if not text:
        return {
            "status": "error",
            "summary": "",
            "message": "No content provided for summarization"
        }
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Try LLM summarization first
    if api_key:
        try:
            prompt = f"""Summarize the following economic news in Korean. 
Make it concise (max 500 chars), easy to understand, and highlight key economic indicators or events.
Format as bullet points if multiple items.

News:\n{text[:3000]}"""
            
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 500,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30.0
            )
            response.raise_for_status()
            
            summary = response.json()["content"][0]["text"]
            
            return {
                "status": "success",
                "summary": summary,
                "content": text,
                "summarization_method": "claude_llm",
                "summary_timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            # Fall back to simple summarization
            pass
    
    # Fallback: simple summarization from titles
    try:
        lines = text.split("\n\n")
        titles = []
        for line in lines:
            if "[" in line and "]" in line:
                title_part = line.split("\n")[0]
                titles.append(title_part)
        
        summary = "오늘의 경제뉴스 요약:\n\n" + "\n".join(titles[:5])
        
        return {
            "status": "success",
            "summary": summary,
            "content": text,
            "summarization_method": "fallback_titles",
            "summary_timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        return {
            "status": "error",
            "summary": "",
            "message": f"Summarization failed: {str(e)}"
        }