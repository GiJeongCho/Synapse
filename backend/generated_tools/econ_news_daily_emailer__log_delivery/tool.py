import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def log_delivery(delivery_status="", send_log="", **kwargs):
    """
    Log delivery status, send_log, and execution details to audit file.
    Creates/appends to a JSON log file with timestamp and status.
    Returns log record and file path.
    """
    try:
        # Get log directory from env or use current directory
        log_dir = os.getenv("LOG_DIR", ".")
        log_file = os.path.join(log_dir, "email_delivery_audit.jsonl")
        
        # Ensure log directory exists
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Create log record
        timestamp = datetime.now().isoformat()
        log_record = {
            "timestamp": timestamp,
            "delivery_status": delivery_status or kwargs.get("status", "unknown"),
            "recipient": kwargs.get("recipient", "wzxcv123@naver.com"),
            "attempt": kwargs.get("attempt", 0),
            "send_log_summary": send_log[:500] if send_log else "",  # Truncate for readability
            "article_count": kwargs.get("article_count", 0),
            "message": kwargs.get("message", "")
        }
        
        # Append to JSONL file (one JSON object per line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_record, ensure_ascii=False) + "\n")
        
        logger.info(f"Logged delivery record to {log_file}")
        
        # Also set up Python logging to file
        log_handler = logging.FileHandler(
            os.path.join(log_dir, "econ_news_agent.log"),
            encoding="utf-8"
        )
        log_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logging.getLogger().addHandler(log_handler)
        
        return {
            "status": "success",
            "log_record": log_record,
            "log_file": log_file,
            "message": f"Delivery logged to {log_file}"
        }
    
    except Exception as e:
        logger.error(f"Failed to log delivery: {str(e)}")
        return {
            "status": "error",
            "log_record": {},
            "log_file": "",
            "message": f"Failed to write log: {str(e)}"
        }
