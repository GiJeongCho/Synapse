def schedule_hourly_execution():
    try:
        cron_expression = '0 * * * *'
        return {
            'status': 'success',
            'cron_expression': cron_expression,
            'description': 'Runs at the start of every hour',
            'frequency': 'hourly'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
