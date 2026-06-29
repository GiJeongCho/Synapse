import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

def email_dispatcher(summary="", summary_text="", content="", **kwargs):
    """
    Send summarized news to wzxcv123@naver.com via SMTP.
    Uses environment variables for SMTP configuration.
    Returns delivery status with timestamp.
    """
    # Read summary from either parameter
    body = summary or summary_text or content or ""
    
    if not body:
        logger.warning("No summary content provided for email dispatch")
        return {
            "status": "error",
            "message": "No summary content to send",
            "delivery_time": datetime.now().isoformat()
        }
    
    # Read SMTP configuration from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    
    recipient = "wzxcv123@naver.com"
    
    # Validate SMTP credentials
    if not smtp_user or not smtp_password:
        logger.error("SMTP_USER or SMTP_PASSWORD not configured")
        return {
            "status": "error",
            "message": "SMTP credentials not configured",
            "delivery_time": datetime.now().isoformat()
        }
    
    try:
        logger.info(f"Preparing email to {recipient}")
        
        # Create HTML email
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        html_body = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #1e88e5; color: white; padding: 15px; border-radius: 5px; }}
                    .content {{ background-color: #f5f5f5; padding: 15px; margin-top: 15px; border-left: 4px solid #1e88e5; }}
                    .footer {{ font-size: 12px; color: #999; margin-top: 20px; text-align: center; }}
                    .bullet {{ margin: 8px 0; line-height: 1.6; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>📰 네이버 경제 뉴스 요약</h2>
                        <p style="margin: 5px 0; font-size: 14px;">Daily Economic News Summary</p>
                    </div>
                    <div class="content">
                        {body.replace(chr(10), '<br>')}
                    </div>
                    <div class="footer">
                        <p>생성 시간: {timestamp}</p>
                        <p>자동 생성된 이메일입니다. 회신하지 마세요.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Create MIME message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[경제뉴스] {timestamp}"
        msg["From"] = smtp_from
        msg["To"] = recipient
        
        # Attach HTML part
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        
        # Connect and send
        logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}")
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        logger.info(f"Authenticated with SMTP server")
        
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email successfully sent to {recipient}")
        return {
            "status": "success",
            "recipient": recipient,
            "timestamp": timestamp,
            "delivery_time": datetime.now().isoformat(),
            "message": f"Email sent to {recipient} at {timestamp}"
        }
    
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP authentication failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "delivery_time": datetime.now().isoformat()
        }
    
    except smtplib.SMTPException as e:
        error_msg = f"SMTP error: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "delivery_time": datetime.now().isoformat()
        }
    
    except Exception as e:
        error_msg = f"Email dispatch failed: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "delivery_time": datetime.now().isoformat()
        }