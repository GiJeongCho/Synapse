import os
import httpx

def summarize_news_digest(content="", articles=None, **kwargs):
    """Summarize news digest using Claude or fallback to title concatenation."""
    if articles is None:
        articles = []
    text = content or ""
    if not text and articles:
        text = "\n".join(f"{a.get('title', '')} - {a.get('summary', '')}" for a in articles)[:5000]
    if not text:
        return {"status": "error", "summary": "", "message": "No content to summarize"}
    
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        summary = "\n".join(f"• {a.get('title', '')}" for a in articles[:10])
        return {"status": "success", "summary": summary, "content": text, "articles": articles}
    
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": f"Summarize these economy news in Korean (3-4 sentences):\n{text}"}]
            },
            timeout=30.0
        )
        resp.raise_for_status()
        summary = resp.json()["content"][0]["text"]
        return {"status": "success", "summary": summary, "content": text, "articles": articles}
    except Exception as e:
        summary = "\n".join(f"• {a.get('title', '')}" for a in articles[:10])
        return {"status": "success", "summary": summary, "content": text, "articles": articles, "note": f"Fallback: {str(e)}"}
