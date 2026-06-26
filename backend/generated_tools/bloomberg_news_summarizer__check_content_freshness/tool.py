import hashlib
import json
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

def check_content_freshness(content_text):
    """Check if content is fresh and not previously summarized."""
    try:
        # Generate content hash
        content_hash = hashlib.sha256(content_text.encode()).hexdigest()
        
        # Cache file path
        cache_file = '/tmp/bloomberg_cache.json'
        cache = {}
        
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        
        # Check if hash exists and is recent
        if content_hash in cache:
            cached_time = datetime.fromisoformat(cache[content_hash])
            if datetime.now() - cached_time < timedelta(hours=1):
                logger.info('Content already processed recently')
                return {'status': 'duplicate', 'is_fresh': False}
        
        # Update cache
        cache[content_hash] = datetime.now().isoformat()
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        
        logger.info('Content is fresh')
        return {'status': 'success', 'is_fresh': True, 'content_hash': content_hash}
    
    except Exception as e:
        logger.error(f'Freshness check error: {e}')
        return {'status': 'error', 'is_fresh': True}  # Default to fresh on error
