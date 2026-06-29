import os
import httpx

def summarize_news(content="", **kwargs):
    """Summarize news content using Claude API."""
    text = content or kwargs.get("content") or ""
    if not text:
        return {"status": "error", "summary": "", "message": "No content to summarize"}
    
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return {"status": "error", "summary": "", "message": "ANTHROPIC_API_KEY not set"}
    
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
                "messages": [{
                    "role": "user",
                    "content": f"Summarize the following economic news in Korean, under 500 characters:\n\n{text[:5000]}"
                }]
            },
            timeout=30.0
        )
        resp.raise_for_status()
        summary = resp.json()["content"][0]["text"]
        return {"status": "success", "summary": summary, "summary_text": summary}
    except Exception as e:
        return {"status": "error", "summary": "", "message": f"Summarization failed: {str(e)[:100]}"}
