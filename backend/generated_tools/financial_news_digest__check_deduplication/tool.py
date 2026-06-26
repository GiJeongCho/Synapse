import json
import os
from datetime import datetime, timedelta

def check_deduplication(articles, memory_file='/tmp/news_digest_memory.json'):
    """
    Check articles against previous digests.
    Returns dict with status and filtered articles.
    """
    try:
        previous_digests = {}
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                data = json.load(f)
                previous_digests = data.get('digests', {})
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        recent_titles = set()
        for digest in previous_digests.values():
            if digest.get('timestamp', '') > cutoff_time:
                recent_titles.update(digest.get('titles', []))
        
        filtered = [a for a in articles if a['title'] not in recent_titles]
        
        current_digest = {
            'timestamp': datetime.utcnow().isoformat(),
            'titles': [a['title'] for a in filtered]
        }
        previous_digests[datetime.utcnow().isoformat()] = current_digest
        
        with open(memory_file, 'w') as f:
            json.dump({'digests': previous_digests}, f)
        
        return {'status': 'success', 'articles': filtered, 'new_count': len(filtered)}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'articles': articles}
