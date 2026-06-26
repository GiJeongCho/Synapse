def summarize_financial_news(html_content):
    try:
        if not html_content or len(html_content) < 20:
            return {'status': 'error', 'message': 'Invalid content'}
        
        lines = html_content.split('\n')
        lines = [l.strip() for l in lines if l.strip() and len(l.strip()) > 5]
        
        summary_lines = lines[:5] if len(lines) > 5 else lines
        summary = 'Financial News Summary:\n' + '\n'.join([f'• {line}' for line in summary_lines])
        
        return {'status': 'success', 'summary': summary}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
