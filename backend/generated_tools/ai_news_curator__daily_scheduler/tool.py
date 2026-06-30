from datetime import datetime
import json

def daily_scheduler(schedule_time="09:00", timezone="Asia/Seoul", **kwargs):
    """Generate schedule configuration for daily 9 AM KST execution"""
    schedule_time = kwargs.get("schedule_time") or schedule_time
    timezone = kwargs.get("timezone") or timezone
    
    try:
        hour, minute = schedule_time.split(":")
        hour = int(hour)
        minute = int(minute)
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time format")
        
        cron_expression = f"{minute} {hour} * * *"
        
        schedule_config = {
            "cron": cron_expression,
            "timezone": timezone,
            "description": f"Daily execution at {schedule_time} {timezone}",
            "workflow": [
                "fetch_ai_news",
                "summarize_news",
                "send_email"
            ],
            "enabled": True
        }
        
        return {
            "status": "success",
            "schedule": schedule_config,
            "cron": cron_expression,
            "next_run": f"Next execution: Daily at {schedule_time} {timezone}",
            "message": f"Schedule configured: {cron_expression} ({timezone})"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Schedule configuration failed: {str(e)}"
        }