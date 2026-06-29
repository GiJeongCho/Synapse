import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

logger = logging.getLogger(__name__)

def send_email_naver(summary="", summary_text="", **kwargs):
    """
    Send summarized news to recipient via SMTP with retry logic.
    Supports 3 retry attempts with exponential backoff.
    Returns delivery status and send log.
    """
    # Read summary from multiple possible input keys
    body = summary or summary_text or kwargs.get("content") or ""
    
    if not body or len(body.strip()) < 10:
        logger.error("No summary content to send")
        return {
            "status": "error",
            "delivery_status": "failed",
            "send_log": "",
            "message": "No summary content provided"
        }
    
    # Read SMTP configuration from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.naver.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    
    recipient = kwargs.get("recipient", "wzxcv123@naver.com")
    subject = kwargs.get("subject", f"[경제뉴스 요약] {datetime.now().strftime('%Y-%m-%d')}")
    
    # Validate credentials
    if not smtp_user or not smtp_password:
        logger.error("SMTP credentials not configured")
        return {
            "status": "error",
            "delivery_status": "failed",
            "send_log": "",
            "message": "SMTP_USER or SMTP_PASSWORD not set in environment"
        }
    
    # Prepare email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = recipient
    msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0900")
    
    # Create HTML and plain text versions
    text_part = MIMEText(body, "plain", "utf-8")
    html_body = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <h2 style="color: #333;">경제뉴스 일일 요약</h2>
    <p style="color: #666; font-size: 12px;">발송 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <hr style="border: 1px solid #ddd;">
    <div style="white-space: pre-wrap; color: #333;">{body}</div>
    <hr style="border: 1px solid #ddd;">
    <p style="color: #999; font-size: 11px;">자동 발송 메일입니다.</p>
    </body></html>"""
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(text_part)
    msg.attach(html_part)
    
    # Retry logic: 3 attempts with exponential backoff
    max_retries = 3
    retry_delay = 2  # seconds
    send_log = []
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Sending email (attempt {attempt}/{max_retries})...")
            send_log.append(f"[Attempt {attempt}] Connecting to {smtp_host}:{smtp_port}...")
            
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                server.starttls()
            
            send_log.append(f"[Attempt {attempt}] Authenticating...")
            server.login(smtp_user, smtp_password)
            
            send_log.append(f"[Attempt {attempt}] Sending message...")
            server.send_message(msg)
            server.quit()
            
            log_entry = f"[Attempt {attempt}] SUCCESS - Email sent to {recipient}"
            send_log.append(log_entry)
            logger.info(log_entry)
            
            return {
                "status": "success",
                "delivery_status": "sent",
                "send_log": "\n".join(send_log),
                "recipient": recipient,
                "attempt": attempt,
                "message": f"Email sent successfully on attempt {attempt}"
            }
        
        except Exception as e:
            error_msg = f"[Attempt {attempt}] FAILED - {str(e)}"
            send_log.append(error_msg)
            logger.warning(error_msg)
            
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                send_log.append(f"[Attempt {attempt}] Retrying in {wait_time}s...")
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed")
    
    return {
        "status": "error",
        "delivery_status": "failed",
        "send_log": "\n".join(send_log),
        "recipient": recipient,
        "attempts": max_retries,
        "message": f"Failed to send email after {max_retries} attempts"
    }
