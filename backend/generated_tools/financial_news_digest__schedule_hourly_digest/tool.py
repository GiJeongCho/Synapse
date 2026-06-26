def schedule_hourly_digest():
    try:
        cron_expression = '0 * * * *'
        return {
            'status': 'success',
            'schedule': cron_expression,
            'description': 'Runs every hour at minute 0',
            'frequency': 'hourly'
        }
    except Exception as e:
        return {'status': 'error', 'message': f'Scheduling failed: {str(e)}'}
