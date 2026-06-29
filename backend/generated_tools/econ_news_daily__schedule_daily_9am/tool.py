from datetime import datetime

def schedule_daily_9am(timezone="Asia/Seoul", **kwargs):
    """
    Generate cron expression for daily 9 AM execution in specified timezone.
    Returns cron schedule and validation info.
    """
    if not timezone:
        timezone = "Asia/Seoul"
    
    cron_expression = "0 9 * * *"
    
    return {
        "status": "success",
        "cron_expression": cron_expression,
        "timezone": timezone,
        "description": "Run daily at 09:00 in Asia/Seoul timezone",
        "next_run": "Tomorrow at 09:00 KST",
        "schedule_type": "daily",
        "hour": 9,
        "minute": 0
    }