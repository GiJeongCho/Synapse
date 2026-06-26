import hashlib
import json
import os
from datetime import datetime, timedelta

def deduplicate_news(articles, memory_file='news_cache.json'):
    """Deduplicate news items using hash comparison."""
    try:
        # Load previous news hashes
        previous_hashes = set()
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                data = json.load(f)
                previous_hashes = set(data.get('hashes', []))
                # Clean old entries (older than 24 hours)
                cutoff = datetime.now() - timedelta(hours=24)
        
        unique_articles = []
        current_hashes = []
        
        for article in articles:
            # Create hash from title and URL
            content_hash = hashlib.md5(
                f"{article['title']}{article['url']}".encode()
            ).hexdigest()
            
            if content_hash not in previous_hashes:
                unique_articles.append(article)
                current_hashes.append(content_hash)
        
        # Save current hashes for next run
        all_hashes = list(previous_hashes) + current_hashes
        with open(memory_file, 'w') as f:
            json.dump({'hashes': all_hashes, 'timestamp': datetime.now().isoformat()}, f)
        
        return {'status': 'success', 'unique_count': len(unique_articles), 'articles': unique_articles}
    except Exception as e:
        return {'status': 'error', 'message': f'Deduplication failed: {str(e)}', 'articles': articles}

functions = ['deduplicate_news']