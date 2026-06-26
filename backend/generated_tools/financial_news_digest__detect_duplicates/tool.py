import json
import os
from pathlib import Path

def detect_duplicates(articles):
    db_path = os.getenv('DUPLICATE_DB_PATH', '/tmp/news_duplicates.json')
    seen = set()
    
    try:
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                data = json.load(f)
                seen = set(data.get('titles', []))
    except Exception as e:
        return {'status': 'error', 'message': f'DB read error: {str(e)}'}
    
    new_articles = []
    for article in articles:
        title = article.get('title', '')
        if title not in seen:
            new_articles.append(article)
            seen.add(title)
    
    try:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with open(db_path, 'w') as f:
            json.dump({'titles': list(seen)}, f)
    except Exception as e:
        return {'status': 'error', 'message': f'DB write error: {str(e)}'}
    
    return {'status': 'success', 'new_articles': new_articles, 'duplicates_removed': len(articles) - len(new_articles)}
