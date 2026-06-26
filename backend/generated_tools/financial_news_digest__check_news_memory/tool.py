import json
import os

def check_news_memory(articles):
    memory_file = '/tmp/news_memory.json'
    previous_urls = set()
    
    try:
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                data = json.load(f)
                previous_urls = set(data.get('urls', []))
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'new_articles': articles}
    
    new_articles = [a for a in articles if a.get('url') not in previous_urls]
    
    try:
        all_urls = previous_urls | {a.get('url') for a in articles}
        with open(memory_file, 'w') as f:
            json.dump({'urls': list(all_urls)}, f)
    except Exception as e:
        pass
    
    return {'status': 'success', 'new_articles': new_articles, 'deduped_count': len(articles) - len(new_articles)}