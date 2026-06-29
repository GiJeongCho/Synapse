import os
import json
from datetime import datetime

def log_delivery(status="", message="", **kwargs):
    """
    Log delivery status and execution details to audit file.
    Creates/appends to logs/delivery_audit.jsonl
    """
    try:
        # Prepare log record
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "status": status or kwargs.get("delivery_status") or "unknown",
            "message": message or kwargs.get("send_log") or "",
            "recipient": kwargs.get("recipient", "wzxcv123@naver.com"),
            "subject": kwargs.get("subject", ""),
            "attempt": kwargs.get("attempt", 1),
            "execution_id": kwargs.get("execution_id", "")
        }
        
        # Ensure logs directory exists
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, "delivery_audit.jsonl")
        
        # Append to JSONL file (one JSON object per line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_record, ensure_ascii=False) + "\n")
        
        return {
            "status": "success",
            "log_record": log_record,
            "log_file": log_file,
            "message": "Delivery logged successfully"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Logging failed: {str(e)}",
            "log_record": {}
        }