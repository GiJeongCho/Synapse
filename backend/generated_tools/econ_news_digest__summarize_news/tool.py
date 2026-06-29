import os
import httpx

def summarize_news(content="", **kwargs):
    """Summarize economic news content using Anthropic Claude."""
    text = content or kwargs.get("content") or ""
    if not text:
        return {"status": "error", "summary": "", "message": "No content to summarize"}
    
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        # Fallback: simple aggregation without LLM
        summary = text[:1000] + "..." if len(text) > 1000 else text
        return {"status": "success", "summary": summary, "content": text}
    
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": f"Summarize key economic insights from this news:\n{text[:5000]}"}]
            },
            timeout=30.0
        )
        resp.raise_for_status()
        summary = resp.json()["content"][0]["text"]
        return {"status": "success", "summary": summary, "content": text}
    except Exception as e:
        return {"status": "error", "summary": "", "message": f"Summarization failed: {str(e)}"}
