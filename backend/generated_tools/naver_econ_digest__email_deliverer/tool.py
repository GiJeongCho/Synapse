import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def email_deliverer(summary="", summary_text="", **kwargs):
    """
    Send summarized digest to wzxcv123@naver.com via SMTP.
    Uses environment variables for SMTP configuration.
    Includes timestamp and HTML formatting.
    """
    try:
        # Read body from summary or summary_text
        body = summary or summary_text or kwargs.get("content") or ""
        
        if not body:
            logger.warning("No summary content to send")
            return {
                "status": "error",
                "message": "No summary content provided"
            }
        
        # SMTP configuration from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)
        
        recipient = "wzxcv123@naver.com"
        
        if not smtp_user or not smtp_password:
            logger.error("SMTP credentials not configured")
            return {
                "status": "error",
                "message": "SMTP_USER or SMTP_PASSWORD not set"
            }
        
        # Create email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[경제뉴스 요약] {datetime.now().strftime('%Y년 %m월 %d일')}"
        msg["From"] = smtp_from
        msg["To"] = recipient
        
        # HTML content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #1f77d2; border-bottom: 2px solid #1f77d2; padding-bottom: 10px;">
                        📰 네이버 경제뉴스 일일 요약
                    </h2>
                    <p style="color: #666; font-size: 12px;">
                        생성 시간: {timestamp}
                    </p>
                    <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #1f77d2; margin: 15px 0;">
                        {body.replace(chr(10), '<br>')}
                    </div>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 11px; text-align: center;">
                        이 메일은 자동으로 생성되었습니다. 문의사항은 관리자에게 연락하세요.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"네이버 경제뉴스 일일 요약\n생성 시간: {timestamp}\n\n{body}"
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        # Send email
        logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}")
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        logger.info(f"Sending email to {recipient}")
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email successfully sent to {recipient}")
        return {
            "status": "success",
            "message": f"Email sent to {recipient}",
            "recipient": recipient,
            "sent_time": timestamp
        }
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {str(e)}")
        return {
            "status": "error",
            "message": f"SMTP authentication failed: {str(e)}"
        }
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        return {
            "status": "error",
            "message": f"SMTP error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error in email deliverer: {str(e)}")
        return {
            "status": "error",
            "message": f"Email delivery exception: {str(e)}"
        }