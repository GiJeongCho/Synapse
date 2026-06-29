import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_news_email(summary="", summary_text="", **kwargs):
    """
    Send economic news summary via email to wzxcv123@naver.com.
    Uses SMTP configuration from environment variables.
    """
    body = summary or summary_text or kwargs.get("content") or ""
    
    if not body:
        return {"status": "error", "message": "No content to send"}
    
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)
        
        if not smtp_user or not smtp_pass:
            return {"status": "error", "message": "SMTP credentials not configured"}
        
        recipient = "wzxcv123@naver.com"
        subject = f"경제뉴스 요약 - {datetime.now().strftime('%Y-%m-%d')}"
        
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
        
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        return {"status": "success", "message": f"Email sent to {recipient}"}
    except Exception as e:
        return {"status": "error", "message": f"Email send failed: {str(e)}"}
