import httpx
import time

def check_robots_txt():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = httpx.get('https://finance.yahoo.com/robots.txt', headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text.lower()
            if 'disallow: /' in content and '/news' not in content:
                return {'status': 'blocked', 'message': 'Yahoo Finance disallows scraping'}
            return {'status': 'allowed', 'message': 'Scraping permitted'}
        return {'status': 'unknown', 'message': 'Could not fetch robots.txt'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
