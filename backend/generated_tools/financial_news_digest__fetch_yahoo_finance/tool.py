import httpx
import os
from datetime import datetime

def fetch_yahoo_finance():
    try:
        headers = {
            'User-Agent': 'FinancialNewsDigestAgent/1.0 (+http://example.com/bot)',
            'Accept': 'text/html,application/xhtml+xml'
        }
        
        # Check robots.txt compliance
        robots_url = 'https://finance.yahoo.com/robots.txt'
        robots_resp = httpx.get(robots_url, headers=headers, timeout=5.0)
        if '/news' in robots_resp.text and 'Disallow: /news' in robots_resp.text:
            return {'status': 'error', 'message': 'Yahoo Finance /news disallowed by robots.txt'}
        
        # Fetch news page
        url = 'https://finance.yahoo.com/news/'
        response = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        
        # Extract headlines (basic parsing)
        content = response.text
        headlines = []
        for line in content.split('\n'):
            if '<h3' in line or '<h2' in line:
                headlines.append(line.strip())
        
        return {
            'status': 'success',
            'content': '\n'.join(headlines[:10]),
            'timestamp': datetime.now().isoformat(),
            'source': 'Yahoo Finance'
        }
    except httpx.TimeoutException:
        return {'status': 'error', 'message': 'Request timeout after 10s'}
    except httpx.HTTPError as e:
        return {'status': 'error', 'message': f'HTTP error: {str(e)}'}
    except Exception as e:
        return {'status': 'error', 'message': f'Fetch failed: {str(e)}'}
