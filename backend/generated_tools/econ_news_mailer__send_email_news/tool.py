import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_news(summary="", summary_text="", **kwargs):
    """Send news summary email with retry logic."""
    body = summary or summary_text or kwargs.get("content") or ""
    if not body:
        return {"status": "error", "message": "no summary to send"}
    
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    recipient = "wzxcv123@naver.com"
    
    if not smtp_user or not smtp_pass:
        return {"status": "error", "message": "SMTP credentials not configured"}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls()
            
            server.login(smtp_user, smtp_pass)
            msg = MIMEMultipart()
            msg["From"] = smtp_from
            msg["To"] = recipient
            msg["Subject"] = "[경제뉴스] 일일 요약"
            msg.attach(MIMEText(body, "plain", "utf-8"))
            server.send_message(msg)
            server.quit()
            return {"status": "success", "message": f"email sent to {recipient}"}
        except Exception as e:
            if attempt == max_retries - 1:
                return {"status": "error", "message": f"email failed after {max_retries} retries: {str(e)}"}
    
    return {"status": "error", "message": "email send failed"}
