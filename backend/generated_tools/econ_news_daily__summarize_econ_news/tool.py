import os
import httpx

def summarize_econ_news(content="", articles=None, **kwargs):
    """
    Summarize economic news using Anthropic Claude API.
    Keeps summary concise (≤500 chars) for email digest.
    """
    text = content or kwargs.get("content") or ""
    
    if not text:
        return {
            "status": "error",
            "summary": "",
            "message": "No content to summarize"
        }
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "summary": "",
            "message": "ANTHROPIC_API_KEY not set"
        }
    
    prompt = f"""Summarize the following economic news in Korean, keeping it under 500 characters. 
Be concise and highlight key economic indicators or events:\n\n{text[:3000]}"""
    
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
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0
        )
        resp.raise_for_status()
        summary = resp.json()["content"][0]["text"]
        return {
            "status": "success",
            "summary": summary[:500],
            "content": summary[:500]
        }
    except Exception as e:
        return {
            "status": "error",
            "summary": "",
            "message": f"Summarization failed: {str(e)}"
        }