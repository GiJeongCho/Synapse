def schedule_hourly():
    cron_expression = '0 * * * *'
    return {
        'status': 'success',
        'schedule': cron_expression,
        'description': 'Runs at the top of every hour',
        'note': 'Use with APScheduler: scheduler.add_job(pipeline, "cron", hour="*", minute="0")'
    }
