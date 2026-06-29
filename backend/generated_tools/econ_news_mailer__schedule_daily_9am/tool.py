def schedule_daily_9am(**kwargs):
    """Return cron expression for 9 AM daily execution."""
    cron_expr = "0 9 * * *"
    return {
        "status": "success",
        "cron": cron_expr,
        "description": "Runs every day at 09:00 (9 AM)",
        "timezone": "Asia/Seoul"
    }
