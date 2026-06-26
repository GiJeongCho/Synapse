import logging
from datetime import datetime, time
import json

logger = logging.getLogger(__name__)

def schedule_daily_task():
    """Define cron schedule for daily news fetching."""
    try:
        # Cron expression: Every 10 minutes from 9 AM to 5 PM, Monday-Friday
        # Format: minute hour day month weekday
        cron_schedule = '*/10 9-16 * * 1-5'  # 9 AM to 4:50 PM, Mon-Fri
        
        schedule_config = {
            'task_id': 'bloomberg_news_fetch',
            'cron_expression': cron_schedule,
            'timezone': 'America/New_York',
            'description': 'Fetch Bloomberg news every 10 minutes during business hours',
            'retry_policy': {
                'max_retries': 3,
                'base_delay_seconds': 5,
                'backoff_multiplier': 2
            },
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f'Schedule configured: {cron_schedule}')
        return {'status': 'success', 'schedule': schedule_config}
    
    except Exception as e:
        logger.error(f'Schedule configuration error: {e}')
        return {'status': 'error', 'message': str(e)}
