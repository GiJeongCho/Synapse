import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from datetime import datetime
import time

def send_email_news(summary="", summary_text="", **kwargs):
    """
    Send summarized news via SMTP with retry logic.
    Supports Naver, Gmail, and custom SMTP servers.
    """
    try:
        # Read input defensively
        body = summary or summary_text or kwargs.get("content") or ""
        
        if not body:
            return {
                "status": "error",
                "delivery_status": "failed",
                "message": "No summary content to send"
            }
        
        # Get SMTP configuration from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.naver.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)
        recipient = os.getenv("RECIPIENT_EMAIL", "wzxcv123@naver.com")
        
        if not smtp_user or not smtp_password:
            return {
                "status": "error",
                "delivery_status": "failed",
                "message": "SMTP credentials not configured (SMTP_USER, SMTP_PASSWORD)"
            }
        
        log_dir = os.getenv("LOG_DIR", "/tmp")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "econ-news-agent.log")
        
        # Email content
        subject = f"[경제뉴스] 일일 경제뉴스 요약 - {datetime.now().strftime('%Y-%m-%d')}"
        
        html_body = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0066cc;">📊 일일 경제뉴스 요약</h2>
            <p style="color: #666; font-size: 12px;">{datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</p>
            <hr style="border: none; border-top: 1px solid #ddd;">
            <div style="white-space: pre-wrap; background: #f9f9f9; padding: 15px; border-radius: 5px;">
{body}
            </div>
            <hr style="border: none; border-top: 1px solid #ddd;">
            <p style="font-size: 11px; color: #999;">자동 생성된 이메일입니다. 회신하지 마세요.</p>
        </body>
        </html>
        """
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Choose SMTP class based on port
                if smtp_port == 465:
                    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
                else:
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                    server.starttls()
                
                server.login(smtp_user, smtp_password)
                
                # Create message
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = smtp_from
                msg["To"] = recipient
                
                msg.attach(MIMEText(body, "plain", "utf-8"))
                msg.attach(MIMEText(html_body, "html", "utf-8"))
                
                # Send email
                server.sendmail(smtp_from, recipient, msg.as_string())
                server.quit()
                
                # Log success
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "function": "send_email_news",
                    "status": "success",
                    "recipient": recipient,
                    "attempt": attempt + 1,
                    "smtp_host": smtp_host
                }
                with open(log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
                
                return {
                    "status": "success",
                    "delivery_status": "sent",
                    "recipient": recipient,
                    "attempt": attempt + 1,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = 2 ** attempt
                    time.sleep(delay)
                else:
                    # All retries exhausted
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "function": "send_email_news",
                        "status": "error",
                        "recipient": recipient,
                        "attempts": max_retries,
                        "error": str(e)
                    }
                    with open(log_file, "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    
                    return {
                        "status": "error",
                        "delivery_status": "failed",
                        "recipient": recipient,
                        "attempts": max_retries,
                        "message": f"Email delivery failed after {max_retries} attempts: {str(e)}"
                    }
        
    except Exception as e:
        return {
            "status": "error",
            "delivery_status": "failed",
            "message": f"Email send failed: {str(e)}"
        }
