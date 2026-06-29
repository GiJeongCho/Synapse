import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

def send_econ_news_email(summary="", summary_text="", **kwargs):
    """
    Send summarized economic news via SMTP email.
    Includes timestamp, retry logic with exponential backoff.
    Reads SMTP credentials from environment variables.
    """
    try:
        # Get email body from summary or summary_text
        body = summary or summary_text or kwargs.get("content") or ""
        
        if not body:
            return {
                "status": "error",
                "message": "No summary content to send"
            }
        
        # Get SMTP configuration from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)
        
        # Validate credentials
        if not smtp_user or not smtp_password:
            return {
                "status": "error",
                "message": "SMTP_USER or SMTP_PASSWORD not set"
            }
        
        # Email configuration
        recipient = "wzxcv123@naver.com"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"[네이버 경제뉴스 요약] {timestamp}"
        
        # Build email body with timestamp
        email_body = f"""네이버 경제뉴스 요약
생성 시간: {timestamp}

{body}

---
자동 생성된 이메일입니다.
"""
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Create SMTP connection
                if smtp_port == 465:
                    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
                else:
                    server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                    server.starttls()
                
                # Login
                server.login(smtp_user, smtp_password)
                
                # Create message
                msg = MIMEMultipart()
                msg["From"] = smtp_from
                msg["To"] = recipient
                msg["Subject"] = subject
                msg.attach(MIMEText(email_body, "plain", "utf-8"))
                
                # Send email
                server.send_message(msg)
                server.quit()
                
                return {
                    "status": "success",
                    "message": f"Email sent to {recipient} at {timestamp}"
                }
            
            except smtplib.SMTPAuthenticationError:
                return {
                    "status": "error",
                    "message": "SMTP authentication failed - check SMTP_USER and SMTP_PASSWORD"
                }
            except smtplib.SMTPException as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return {
                        "status": "error",
                        "message": f"SMTP error after {max_retries} retries: {str(e)}"
                    }
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return {
                        "status": "error",
                        "message": f"Email send error after {max_retries} retries: {str(e)}"
                    }
        
        return {
            "status": "error",
            "message": "Failed to send email after all retries"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error in email dispatcher: {str(e)}"
        }