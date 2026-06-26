import sqlite3
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def deduplicate_articles(articles):
    db_path = os.getenv('DEDUP_DB_PATH', '/tmp/finance_articles.db')
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_articles (
                url TEXT PRIMARY KEY,
                title TEXT,
                timestamp INTEGER
            )
        ''')
        conn.commit()
        
        new_articles = []
        for article in articles:
            url = article.get('url', '')
            if not url:
                continue
            
            cursor.execute('SELECT url FROM seen_articles WHERE url = ?', (url,))
            if not cursor.fetchone():
                new_articles.append(article)
                cursor.execute(
                    'INSERT INTO seen_articles (url, title, timestamp) VALUES (?, ?, ?)',
                    (url, article.get('title', ''), article.get('timestamp', 0))
                )
        
        conn.commit()
        conn.close()
        
        logger.info(f'Deduplicated: {len(articles)} -> {len(new_articles)} unique articles')
        return {'status': 'success', 'articles': new_articles, 'count': len(new_articles)}
    except Exception as e:
        logger.error(f'Deduplication error: {e}')
        return {'status': 'error', 'message': str(e), 'articles': articles}
