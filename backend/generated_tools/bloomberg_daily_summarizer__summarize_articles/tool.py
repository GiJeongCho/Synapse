def summarize_articles(content="", articles=None, **kwargs):
    """
    Summarize articles using extractive method (select top sentences).
    Keeps summaries concise and relevant.
    """
    try:
        if articles is None:
            articles = []
        
        if not articles:
            return {"status": "error", "summary": "", "error_message": "No articles to summarize"}
        
        summaries = []
        for article in articles[:10]:  # Cap at 10 articles
            title = article.get("title", "")
            summary = article.get("summary", "")
            link = article.get("link", "")
            
            # Extractive summarization: take first 2 sentences
            sentences = summary.split('. ')
            extracted = '. '.join(sentences[:2]) if sentences else summary
            extracted = (extracted[:300] + '...') if len(extracted) > 300 else extracted
            
            summaries.append({
                "title": title,
                "summary": extracted,
                "link": link
            })
        
        # Combine all summaries into single text
        summary_text = "\n\n".join([
            f"📰 {s['title']}\n{s['summary']}\n🔗 {s['link']}"
            for s in summaries
        ])
        
        # Truncate to 15000 chars max
        summary_text = summary_text[:15000]
        
        return {
            "status": "success",
            "summary": summary_text,
            "summary_text": summary_text,
            "article_count": len(summaries)
        }
    except Exception as e:
        return {"status": "error", "summary": "", "error_message": f"Summarization failed: {str(e)}"}
