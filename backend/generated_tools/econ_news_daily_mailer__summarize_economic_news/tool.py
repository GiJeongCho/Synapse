import os
import httpx
import json
from datetime import datetime

def summarize_economic_news(content="", html_content="", content_text="", **kwargs):
    """
    Summarize economic news using Anthropic Claude API.
    Falls back to simple title-based summary if API unavailable.
    """
    try:
        # Read input defensively
        text = content or html_content or content_text or ""
        
        if not text:
            return {
                "status": "error",
                "summary": "",
                "content": "",
                "message": "No content provided for summarization"
            }
        
        log_dir = os.getenv("LOG_DIR", "/tmp")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "econ-news-agent.log")
        
        # Try Anthropic API first
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if api_key:
            try:
                prompt = f"""Summarize the following economic news articles in Korean. 
Provide a concise summary (max 500 chars) highlighting key economic trends and impacts.
Format: Use bullet points for main points.

News:\n{text}"""
                
                resp = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                resp.raise_for_status()
                summary = resp.json()["content"][0]["text"]
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "function": "summarize_economic_news",
                    "status": "success",
                    "method": "anthropic_api",
                    "summary_length": len(summary)
                }
                with open(log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
                
                return {
                    "status": "success",
                    "summary": summary,
                    "content": text,
                    "method": "anthropic_api"
                }
            except Exception as e:
                # Fall back to simple summary
                pass
        
        # Fallback: Simple summary from article titles
        lines = text.split("\n")
        title_lines = [l for l in lines if l.strip() and not l.startswith("Source:")]
        summary = "\n".join(title_lines[:5])  # Top 5 articles
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "function": "summarize_economic_news",
            "status": "success",
            "method": "fallback_titles",
            "summary_length": len(summary)
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return {
            "status": "success",
            "summary": summary,
            "content": text,
            "method": "fallback_titles"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "summary": "",
            "content": "",
            "message": f"Summarization failed: {str(e)}"
        }
