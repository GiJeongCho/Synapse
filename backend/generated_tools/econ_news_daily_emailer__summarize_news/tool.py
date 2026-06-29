import os
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def summarize_news(content="", html_content="", content_text="", **kwargs):
    """
    Summarize economic news content using Anthropic Claude API.
    Falls back to simple title-based summary if LLM unavailable.
    Returns summary text.
    """
    # Read content from multiple possible input keys
    text = content or html_content or content_text or ""
    
    if not text or len(text.strip()) < 10:
        logger.warning("No content provided for summarization")
        return {
            "status": "error",
            "summary": "",
            "content": "",
            "message": "No content to summarize"
        }
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, using fallback summary")
        # Fallback: extract titles and create simple summary
        lines = text.split("\n\n")
        summary = "\n".join(lines[:5])  # Take first 5 articles
        return {
            "status": "success",
            "summary": summary,
            "content": text,
            "method": "fallback",
            "message": "Summary created without LLM (fallback mode)"
        }
    
    try:
        logger.info("Calling Anthropic Claude API for summarization...")
        
        prompt = f"""Summarize the following economic news articles in a concise, easy-to-understand format. 
Include key points and main takeaways. Keep it under 500 words.

News content:
{text}

Provide a well-structured summary with bullet points for main news items."""
        
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
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30.0
        )
        
        resp.raise_for_status()
        result = resp.json()
        summary = result["content"][0]["text"]
        
        logger.info("Successfully summarized news with Claude")
        return {
            "status": "success",
            "summary": summary,
            "content": text,
            "method": "claude",
            "message": "News summarized successfully"
        }
    
    except Exception as e:
        logger.error(f"Claude API error: {str(e)}, falling back to simple summary")
        # Fallback to simple summary
        lines = text.split("\n\n")
        summary = "\n".join(lines[:5])
        return {
            "status": "success",
            "summary": summary,
            "content": text,
            "method": "fallback",
            "message": f"LLM failed ({str(e)}), using fallback summary"
        }
