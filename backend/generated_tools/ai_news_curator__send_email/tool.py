import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email(summary="", summary_text="", **kwargs):
    """Send email with AI news digest"""
    body = summary or summary_text or kwargs.get("content") or ""
    
    if not body:
        return {
            "status": "error",
            "message": "No content to send"
        }
    
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    
    if not smtp_user or not smtp_password:
        return {
            "status": "error",
            "message": "SMTP credentials not configured (SMTP_USER, SMTP_PASSWORD required)"
        }
    
    recipient = "kny8664@naver.com"
    subject = f"🤖 AI 뉴스 다이제스트 - {datetime.now().strftime('%Y년 %m월 %d일')}"
    
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_from
        msg["To"] = recipient
        msg["Subject"] = subject
        
        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return {
            "status": "success",
            "message": f"Email sent successfully to {recipient}",
            "recipient": recipient,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Email sending failed: {str(e)}"
        }