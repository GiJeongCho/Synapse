import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)

def daily_scheduler(start_hour=9, start_minute=0, interval_minutes=10, end_hour=18, **kwargs):
    """
    Generate cron schedule for daily economic news workflow.
    Triggers at 9 AM, then every 10 minutes until 6 PM (18:00).
    Returns cron expression and schedule metadata.
    
    Schedule breakdown:
    - Start: 09:00 (9 AM)
    - Interval: 10 minutes
    - End: 18:00 (6 PM)
    - Triggers: 09:00, 09:10, 09:20, ..., 17:50
    """
    
    try:
        logger.info(f"Generating daily schedule: start {start_hour}:{start_minute:02d}, "
                   f"interval {interval_minutes} min, end {end_hour}:00")
        
        # Generate list of trigger times
        trigger_times = []
        current_hour = start_hour
        current_minute = start_minute
        
        while current_hour < end_hour or (current_hour == end_hour and current_minute == 0):
            trigger_times.append(f"{current_hour:02d}:{current_minute:02d}")
            
            current_minute += interval_minutes
            if current_minute >= 60:
                current_hour += current_minute // 60
                current_minute = current_minute % 60
            
            if current_hour >= end_hour:
                break
        
        # Build cron expression for APScheduler
        # Format: minute hour day month day_of_week
        # For multiple times, we need multiple cron entries or use a list
        minutes = [str(t.split(":")[1]) for t in trigger_times]
        hours = [str(t.split(":")[0]) for t in trigger_times]
        
        # Create cron-like expression (APScheduler format)
        cron_expression = f"cron(minute='{','.join(minutes)}' hour='{','.join(hours)}' day_of_week='mon-fri')"
        
        schedule_config = {
            "status": "success",
            "schedule_type": "daily_recurring",
            "start_time": f"{start_hour:02d}:{start_minute:02d}",
            "end_time": f"{end_hour:02d}:00",
            "interval_minutes": interval_minutes,
            "trigger_times": trigger_times,
            "total_triggers_per_day": len(trigger_times),
            "cron_expression": cron_expression,
            "apscheduler_config": {
                "trigger": "cron",
                "hour": ",".join(hours),
                "minute": ",".join(minutes),
                "day_of_week": "mon-fri",
                "timezone": "Asia/Seoul"
            },
            "retry_config": {
                "max_retries": 3,
                "backoff_factor": 2,
                "backoff_max": 300
            },
            "generated_at": datetime.now().isoformat(),
            "description": f"Fetch and email economic news daily from {start_hour:02d}:{start_minute:02d} "
                          f"every {interval_minutes} minutes until {end_hour}:00 (Seoul time)"
        }
        
        logger.info(f"Schedule generated: {len(trigger_times)} triggers per day")
        logger.info(f"Trigger times: {', '.join(trigger_times[:5])}... (showing first 5)")
        
        return schedule_config
    
    except Exception as e:
        error_msg = f"Schedule generation failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "generated_at": datetime.now().isoformat()
        }