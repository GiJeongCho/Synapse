from datetime import datetime

def summarize_news(unique_articles):
    """
    Create a formatted summary of news articles.
    Returns dict with status and summary text.
    """
    try:
        if not unique_articles:
            summary = "No new financial news articles to report."
        else:
            lines = []
            lines.append(f"Financial News Digest - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("=" * 60)
            lines.append(f"\nFound {len(unique_articles)} new articles:\n")
            
            for idx, article in enumerate(unique_articles, 1):
                lines.append(f"{idx}. {article['title']}")
                lines.append(f"   Link: {article['link']}")
                lines.append(f"   Source: {article['source']}\n")
            
            lines.append("=" * 60)
            lines.append("End of Digest")
            summary = "\n".join(lines)
        
        return {
            'status': 'success',
            'summary': summary,
            'article_count': len(unique_articles)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'summary': ''}
