def schedule_hourly_task():
    cron_expr = '0 * * * *'
    return {
        'status': 'success',
        'cron_expression': cron_expr,
        'description': 'Run at minute 0 of every hour',
        'note': 'Use systemd timer, cron, or APScheduler to execute agent workflow'
    }
