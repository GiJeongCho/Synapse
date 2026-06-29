from datetime import datetime
import pytz

def schedule_daily_job(start_time="09:00", timezone="Asia/Seoul", interval_minutes=10, **kwargs):
    """
    Generate scheduling configuration for 9 AM daily execution.
    Returns cron expression and rate limit info.
    """
    try:
        # Parse start time
        hour, minute = map(int, start_time.split(':'))
        
        # Validate timezone
        try:
            tz = pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            tz = pytz.timezone("Asia/Seoul")
        
        # Generate cron expression for 9 AM daily
        cron_expr = f"{minute} {hour} * * *"  # minute hour * * *
        
        # Calculate rate limit: 6 requests per hour (10-min intervals)
        requests_per_hour = 60 // interval_minutes
        
        # Validate interval
        if interval_minutes < 5:
            return {
                "status": "error",
                "error_message": "Interval must be at least 5 minutes"
            }
        
        config = {
            "cron_expression": cron_expr,
            "start_time": start_time,
            "timezone": str(tz),
            "interval_minutes": interval_minutes,
            "requests_per_hour": requests_per_hour,
            "max_daily_requests": requests_per_hour * 8,  # 8 hours of operation
            "description": f"Run every {interval_minutes} minutes starting at {start_time} {timezone}"
        }
        
        return {
            "status": "success",
            "schedule": config,
            "cron_expression": cron_expr
        }
    except ValueError as e:
        return {"status": "error", "error_message": f"Invalid time format: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error_message": f"Scheduling failed: {str(e)}"}
