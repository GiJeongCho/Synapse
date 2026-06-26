def schedule_hourly_job():
    cron_expression = '0 * * * *'
    return {
        'status': 'success',
        'cron': cron_expression,
        'description': 'Runs at the start of every hour',
        'implementation': 'Use APScheduler or system cron with: 0 * * * * /usr/bin/python3 /path/to/agent.py'
    }
