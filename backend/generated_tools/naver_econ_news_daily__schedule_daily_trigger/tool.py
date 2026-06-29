import os
from datetime import datetime

def schedule_daily_trigger(hour=9, minute=0, timezone="Asia/Seoul", **kwargs):
    """
    Generate cron expression for daily 9:00 AM KST trigger.
    Returns cron string and scheduling metadata.
    """
    hour = kwargs.get("hour") or hour
    minute = kwargs.get("minute") or minute
    timezone = kwargs.get("timezone") or timezone
    
    # Validate inputs
    if not isinstance(hour, int) or hour < 0 or hour > 23:
        hour = 9
    if not isinstance(minute, int) or minute < 0 or minute > 59:
        minute = 0
    
    # Generate cron expression (minute hour * * *)
    cron_expression = f"{minute} {hour} * * *"
    
    return {
        "status": "success",
        "cron_expression": cron_expression,
        "schedule_type": "daily",
        "hour": hour,
        "minute": minute,
        "timezone": timezone,
        "description": f"Trigger workflow daily at {hour:02d}:{minute:02d} {timezone}",
        "next_run_info": "Scheduler will execute at specified time using APScheduler or system cron"
    }
