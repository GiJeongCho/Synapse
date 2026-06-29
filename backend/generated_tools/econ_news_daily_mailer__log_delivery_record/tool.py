import os
import json
from datetime import datetime

def log_delivery_record(delivery_status="", send_log="", **kwargs):
    """
    Log delivery records and execution status for audit trail.
    Maintains persistent record of all workflow executions.
    """
    try:
        log_dir = os.getenv("LOG_DIR", "/tmp")
        os.makedirs(log_dir, exist_ok=True)
        
        # Main log file
        log_file = os.path.join(log_dir, "econ-news-agent.log")
        
        # Separate delivery log file
        delivery_log_file = os.path.join(log_dir, "econ-news-delivery.log")
        
        # Extract delivery info from kwargs
        status = kwargs.get("status", "unknown")
        recipient = kwargs.get("recipient", "wzxcv123@naver.com")
        attempt = kwargs.get("attempt", 0)
        message = kwargs.get("message", "")
        
        # Create delivery record
        delivery_record = {
            "timestamp": datetime.now().isoformat(),
            "function": "log_delivery_record",
            "delivery_status": delivery_status or status,
            "recipient": recipient,
            "attempt": attempt,
            "message": message,
            "log_record": "created"
        }
        
        # Write to delivery log
        with open(delivery_log_file, "a") as f:
            f.write(json.dumps(delivery_record) + "\n")
        
        # Also write to main log
        with open(log_file, "a") as f:
            f.write(json.dumps(delivery_record) + "\n")
        
        # Read recent delivery history (last 10 records)
        recent_records = []
        if os.path.exists(delivery_log_file):
            with open(delivery_log_file, "r") as f:
                lines = f.readlines()
                recent_records = [json.loads(line) for line in lines[-10:] if line.strip()]
        
        return {
            "status": "success",
            "log_record": "created",
            "log_file": delivery_log_file,
            "timestamp": datetime.now().isoformat(),
            "recent_deliveries": len(recent_records),
            "delivery_status": delivery_status or status
        }
        
    except Exception as e:
        return {
            "status": "error",
            "log_record": "failed",
            "message": f"Logging failed: {str(e)}"
        }
