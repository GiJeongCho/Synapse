def schedule_hourly():
    return {
        'status': 'success',
        'schedule': '0 * * * *',
        'description': 'Run at minute 0 of every hour',
        'implementation': 'Use APScheduler or system cron: 0 * * * * /path/to/agent.py',
        'rate_limit': {'requests_per_hour': 60, 'backoff_seconds': 5}
    }
