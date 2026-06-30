def daily_scheduler(schedule_time="09:00", timezone="Asia/Seoul", **kwargs):
    """Returns cron expression for scheduling - use with external scheduler"""
    try:
        schedule_time = kwargs.get("schedule_time") or schedule_time
        timezone = kwargs.get("timezone") or timezone
        
        # Parse time
        hour, minute = schedule_time.split(":")
        hour = int(hour)
        minute = int(minute)
        
        # Cron expression: minute hour day month weekday
        # For 9:00 AM daily: 0 9 * * *
        cron_expression = f"{minute} {hour} * * *"
        
        return {
            "status": "success",
            "cron_expression": cron_expression,
            "timezone": timezone,
            "schedule_time": schedule_time,
            "description": f"Runs daily at {schedule_time} {timezone}",
            "setup_instructions": (
                "Add this to your crontab (crontab -e):\n"
                f"TZ={timezone} {cron_expression} /path/to/agent_runner.sh\n\n"
                "Or use a scheduler service like:"
                "- GitHub Actions (schedule workflow)\n"
                "- Cloud Functions (Cloud Scheduler)\n"
                "- Heroku Scheduler\n"
                "- systemd timer (Linux)\n\n"
                "Ensure all environment variables (SMTP_*, ANTHROPIC_API_KEY) are set."
            )
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Scheduler config error: {str(e)}"
        }
