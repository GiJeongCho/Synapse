def schedule_daily_execution(**kwargs):
    """
    Return cron expression for every 10 minutes starting at 9 AM.
    Cron format: minute hour day month day_of_week
    Every 10 minutes from 9 AM to 5:59 PM (business hours).
    """
    # Every 10 minutes during 9 AM - 5:59 PM: */10 9-17 * * *
    # This runs at: 9:00, 9:10, 9:20, ..., 17:50
    cron_expression = "*/10 9-17 * * *"
    
    return {
        "status": "success",
        "cron_expression": cron_expression,
        "description": "Every 10 minutes from 9 AM to 5:59 PM daily",
        "timezone": "UTC",
        "schedule_type": "cron"
    }
