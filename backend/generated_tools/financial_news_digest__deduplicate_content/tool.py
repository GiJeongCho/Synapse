import hashlib
import json
import os

def deduplicate_content(articles, previous_hashes=None):
    try:
        if previous_hashes is None:
            previous_hashes = []
        
        unique_articles = []
        current_hashes = []
        
        for article in articles:
            article_str = json.dumps(article, sort_keys=True)
            article_hash = hashlib.sha256(article_str.encode()).hexdigest()
            current_hashes.append(article_hash)
            
            if article_hash not in previous_hashes:
                unique_articles.append(article)
        
        return {
            'status': 'success',
            'unique_articles': unique_articles,
            'current_hashes': current_hashes,
            'duplicates_removed': len(articles) - len(unique_articles)
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
