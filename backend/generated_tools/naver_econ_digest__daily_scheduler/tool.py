import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def daily_scheduler(**kwargs):
    """
    Generate APScheduler cron configuration for 9:10 AM KST daily execution.
    Returns cron expression and retry configuration.
    
    This tool returns the scheduling configuration that should be used by
    the orchestrator to set up the actual scheduled job.
    """
    try:
        logger.info("Generating daily scheduler configuration")
        
        # APScheduler cron configuration for 9:10 AM KST
        scheduler_config = {
            "status": "success",
            "trigger": "cron",
            "hour": 9,
            "minute": 10,
            "timezone": "Asia/Seoul",
            "job_name": "naver_econ_digest_daily",
            "description": "Daily economic news digest at 9:10 AM KST"
        }
        
        # Retry configuration with exponential backoff
        retry_config = {
            "max_retries": 3,
            "retry_strategy": "exponential_backoff",
            "initial_delay": 60,  # 1 minute
            "backoff_factor": 2,  # Double delay each retry
            "max_delay": 600  # Cap at 10 minutes
        }
        
        # Workflow pipeline configuration
        workflow_pipeline = {
            "steps": [
                {
                    "step": 1,
                    "tool": "naver_econ_news_fetcher",
                    "description": "Fetch latest economic news",
                    "timeout": 30,
                    "required": True
                },
                {
                    "step": 2,
                    "tool": "news_summarizer",
                    "description": "Summarize articles",
                    "timeout": 45,
                    "required": True,
                    "input_from": "naver_econ_news_fetcher"
                },
                {
                    "step": 3,
                    "tool": "email_deliverer",
                    "description": "Send email digest",
                    "timeout": 30,
                    "required": True,
                    "input_from": "news_summarizer"
                }
            ]
        }
        
        next_run = _calculate_next_run()
        
        logger.info(f"Scheduler configured for 9:10 AM KST daily")
        logger.info(f"Next scheduled run: {next_run}")
        
        return {
            "status": "success",
            "scheduler_config": scheduler_config,
            "retry_config": retry_config,
            "workflow_pipeline": workflow_pipeline,
            "next_run": next_run,
            "configured_time": datetime.now().__str__()
        }
        
    except Exception as e:
        logger.error(f"Error in scheduler configuration: {str(e)}")
        return {
            "status": "error",
            "message": f"Scheduler configuration failed: {str(e)}"
        }

def _calculate_next_run():
    """
    Calculate the next scheduled run time (9:10 AM KST).
    """
    try:
        from datetime import datetime, timedelta, timezone
        import pytz
        
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        # Create 9:10 AM today
        next_run = now.replace(hour=9, minute=10, second=0, microsecond=0)
        
        # If 9:10 AM has already passed today, schedule for tomorrow
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        
        return next_run.isoformat()
        
    except ImportError:
        # Fallback if pytz not available
        now = datetime.now()
        next_run = now.replace(hour=9, minute=10, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        return next_run.isoformat()
    except Exception as e:
        logger.warning(f"Could not calculate next run: {str(e)}")
        return "Unable to calculate"