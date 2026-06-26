def summarize_news_content(articles):
    """Create a concise summary of news articles."""
    try:
        if not articles:
            return {'status': 'error', 'message': 'No articles to summarize'}
        
        # Build summary from article titles
        summary_lines = []
        summary_lines.append('=== Financial News Digest ===' + '\n')
        summary_lines.append(f'Total Articles: {len(articles)}\n')
        summary_lines.append('-' * 40 + '\n')
        
        word_count = 0
        max_words = 300
        
        for idx, article in enumerate(articles, 1):
            title = article['title']
            url = article['url']
            
            # Add article with link
            line = f"{idx}. {title}\n   Link: {url}\n"
            summary_lines.append(line)
            word_count += len(title.split())
            
            if word_count >= max_words:
                break
        
        summary_lines.append('-' * 40 + '\n')
        summary_lines.append('Digest generated automatically. Please review full articles for details.\n')
        
        summary_text = ''.join(summary_lines)
        return {'status': 'success', 'summary': summary_text, 'word_count': word_count}
    except Exception as e:
        return {'status': 'error', 'message': f'Summarization failed: {str(e)}'}

functions = ['summarize_news_content']