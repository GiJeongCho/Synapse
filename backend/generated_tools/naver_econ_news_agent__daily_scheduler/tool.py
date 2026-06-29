import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def daily_scheduler(**kwargs):
    """
    Return cron expression for scheduling the workflow.
    Runs every 10 minutes starting at 9 AM daily (KST timezone).
    
    This tool returns the cron configuration that should be used with APScheduler.
    The agent runtime will use this to set up the actual scheduled job.
    """
    try:
        # Cron expression: every 10 minutes from 9 AM to 11:59 PM
        # Format: minute hour day month day_of_week
        # */10 = every 10 minutes
        # 9-23 = 9 AM to 11 PM (24-hour format)
        # * = every day
        # * = every month
        # * = every day of week
        
        cron_expression = '*/10 9-23 * * *'
        timezone = 'Asia/Seoul'  # KST
        
        logger.info(f"Scheduler configured: {cron_expression} (timezone: {timezone})")
        
        return {
            'status': 'success',
            'cron_expression': cron_expression,
            'timezone': timezone,
            'description': 'Every 10 minutes from 9 AM to 11:59 PM daily (KST)',
            'next_run': _calculate_next_run()
        }
    
    except Exception as e:
        logger.error(f"Scheduler configuration error: {str(e)}")
        return {
            'status': 'error',
            'message': f'Scheduler configuration failed: {str(e)}'
        }

def _calculate_next_run():
    """
    Calculate the next scheduled run time.
    """
    try:
        from datetime import datetime, timedelta
        import pytz
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        # If before 9 AM, next run is today at 9 AM
        if now.hour < 9:
            next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        # If after 11:59 PM, next run is tomorrow at 9 AM
        elif now.hour >= 23:
            next_run = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        # Otherwise, next run is in 10 minutes (rounded to nearest 10-min interval)
        else:
            minutes = ((now.minute // 10) + 1) * 10
            if minutes >= 60:
                next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(minute=minutes, second=0, microsecond=0)
        
        return next_run.strftime('%Y-%m-%d %H:%M:%S %Z')
    except Exception as e:
        logger.error(f"Next run calculation error: {str(e)}")
        return 'Unable to calculate'
