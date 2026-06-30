import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime

def send_email(summary="", summary_text="", recipient="kny8664@naver.com", **kwargs):
    """Send email with retry logic and HTML formatting"""
    try:
        # Get email body
        body = summary or summary_text or kwargs.get("content") or ""
        if not body:
            return {
                "status": "error",
                "message": "No content to send"
            }
        
        # Get SMTP credentials from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM") or smtp_user
        
        if not smtp_user or not smtp_password:
            return {
                "status": "error",
                "message": "SMTP_USER or SMTP_PASSWORD not set"
            }
        
        # Override recipient if provided in kwargs
        recipient = kwargs.get("recipient") or recipient
        subject = kwargs.get("subject") or f"🤖 AI 뉴스 요약 - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Create HTML email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = recipient
        
        # Plain text version
        text_part = MIMEText(body, "plain", "utf-8")
        
        # HTML version
        html_body = f"""
        <html>
          <head>
            <meta charset="utf-8">
          </head>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <pre style="white-space: pre-wrap; font-family: inherit;">{body}</pre>
              <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
              <p style="font-size: 12px; color: #666;">
                이 이메일은 AI 뉴스 큐레이터 에이전트가 자동으로 발송했습니다.<br>
                수신을 원하지 않으시면 SMTP 설정을 비활성화하세요.
              </p>
            </div>
          </body>
        </html>
        """
        html_part = MIMEText(html_body, "html", "utf-8")
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
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
                    "message": f"Email sent to {recipient}",
                    "recipient": recipient,
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
        
        return {
            "status": "error",
            "message": "Max retries exceeded"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Email send error: {str(e)}"
        }
