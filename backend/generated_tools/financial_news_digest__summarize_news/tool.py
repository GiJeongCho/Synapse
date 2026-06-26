def summarize_news(html_content):
    if not html_content or len(html_content) < 10:
        return {'status': 'skipped', 'summary': 'No content to summarize'}
    
    try:
        sentences = html_content.split('|')
        summary_sentences = sentences[:3] if len(sentences) > 3 else sentences
        summary = ' '.join(summary_sentences)
        
        if len(summary) > 150:
            summary = summary[:150] + '...'
        
        formatted = f"""FINANCIAL NEWS DIGEST\n{'='*40}\n{summary}\n\nGenerated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"""
        
        return {'status': 'success', 'summary': formatted}
    except Exception as e:
        return {'status': 'error', 'summary': '', 'message': str(e)}
