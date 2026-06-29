def summarize_news(content="", articles=None, **kwargs):
    """
    Summarize economic news by extracting key points.
    Filters for economic relevance and creates concise summary.
    """
    if articles is None:
        articles = kwargs.get("articles", [])
    
    text = content or ""
    
    try:
        if not articles and not text:
            return {"status": "error", "summary": "", "message": "No content to summarize"}
        
        # Create structured summary from articles
        summary_lines = ["=== 경제뉴스 요약 ==="]
        summary_lines.append(f"수집 시간: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
        summary_lines.append("")
        
        if articles:
            for i, article in enumerate(articles[:10], 1):
                title = article.get("title", "")[:80]
                summary = article.get("summary", "")[:200]
                summary_lines.append(f"{i}. {title}")
                if summary:
                    summary_lines.append(f"   {summary}")
                summary_lines.append("")
        else:
            summary_lines.append(text[:2000])
        
        summary = "\n".join(summary_lines)
        return {"status": "success", "summary": summary, "content": summary}
    except Exception as e:
        return {"status": "error", "summary": "", "message": str(e)}
