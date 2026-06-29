import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email_naver(summary="", summary_text="", **kwargs):
    """
    Send email via Naver SMTP with retry logic.
    Supports 3 attempts with exponential backoff (1s, 2s, 4s).
    """
    body = summary or summary_text or kwargs.get("content") or ""
    
    if not body:
        return {
            "status": "error",
            "message": "No summary content to send"
        }
    
    # Email configuration from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.naver.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    
    recipient = "wzxcv123@naver.com"
    subject = f"[경제뉴스 요약] {datetime.now().strftime('%Y년 %m월 %d일')}"
    
    if not smtp_user or not smtp_password:
        return {
            "status": "error",
            "message": "SMTP credentials not configured (SMTP_USER, SMTP_PASSWORD)"
        }
    
    # Retry logic: 3 attempts with exponential backoff
    max_retries = 3
    backoff_times = [1, 2, 4]  # seconds
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = recipient
            
            # HTML version with styling
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #0066cc;">경제뉴스 일일 요약</h2>
                <p style="color: #666; font-size: 12px;">{datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
                <hr style="border: 1px solid #ddd;">
                <div style="white-space: pre-wrap; background: #f9f9f9; padding: 15px; border-radius: 5px;">
{body}
                </div>
                <hr style="border: 1px solid #ddd;">
                <p style="font-size: 11px; color: #999;">자동 생성된 이메일입니다.</p>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            # Connect and send
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                server.starttls()
            
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            
            return {
                "status": "success",
                "message": f"Email sent successfully to {recipient}",
                "recipient": recipient,
                "subject": subject,
                "attempt": attempt + 1,
                "send_timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                wait_time = backoff_times[attempt]
                time.sleep(wait_time)
            continue
    
    return {
        "status": "error",
        "message": f"Email send failed after {max_retries} attempts: {last_error}",
        "recipient": recipient,
        "attempts": max_retries
    }