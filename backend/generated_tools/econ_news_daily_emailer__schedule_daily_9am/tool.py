import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

def schedule_daily_9am(trigger_time="09:00", **kwargs):
    """
    Schedule the news fetch-summarize-send workflow to run daily at 9:00 AM.
    Returns cron expression and scheduler status.
    """
    try:
        hour, minute = map(int, trigger_time.split(":"))
        cron_expr = f"{minute} {hour} * * *"
        
        scheduler = BackgroundScheduler()
        if not scheduler.running:
            scheduler.start()
            logger.info(f"Scheduler started. Cron: {cron_expr}")
        
        return {
            "status": "success",
            "cron_expression": cron_expr,
            "trigger_time": trigger_time,
            "scheduler_active": scheduler.running,
            "message": f"Scheduled to run daily at {trigger_time}"
        }
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}")
        return {
            "status": "error",
            "cron_expression": "",
            "message": f"Failed to schedule: {str(e)}"
        }
