import os
import json
import time
from datetime import datetime
import pytz

def schedule_daily_trigger(dry_run="false", **kwargs):
    """
    Schedule trigger for 9 AM KST daily execution.
    Returns trigger signal to start the workflow.
    """
    try:
        tz = pytz.timezone('Asia/Seoul')
        now = datetime.now(tz)
        trigger_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # If past 9 AM today, next trigger is tomorrow at 9 AM
        if now >= trigger_time:
            from datetime import timedelta
            trigger_time = trigger_time + timedelta(days=1)
        
        seconds_until_trigger = (trigger_time - now).total_seconds()
        
        log_dir = os.getenv("LOG_DIR", "/tmp")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "econ-news-agent.log")
        
        log_entry = {
            "timestamp": now.isoformat(),
            "function": "schedule_daily_trigger",
            "status": "scheduled",
            "next_trigger": trigger_time.isoformat(),
            "seconds_until_trigger": seconds_until_trigger,
            "dry_run": dry_run == "true"
        }
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return {
            "status": "success",
            "trigger_signal": "ready" if dry_run == "true" else "scheduled",
            "next_trigger_time": trigger_time.isoformat(),
            "seconds_until_trigger": seconds_until_trigger,
            "dry_run": dry_run == "true"
        }
    except Exception as e:
        return {
            "status": "error",
            "trigger_signal": "",
            "message": f"Schedule trigger failed: {str(e)}"
        }
