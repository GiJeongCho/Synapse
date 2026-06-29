import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email_summary(summary="", summary_text="", **kwargs):
    """
    Send summarized news via SMTP email.
    Reads summary from summary or summary_text parameter.
    """
    # Get email content
    body = summary or summary_text or kwargs.get("content") or ""
    
    if not body:
        return {
            "status": "error",
            "message": "No summary content provided"
        }
    
    # Get SMTP credentials from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    recipient = os.getenv("RECIPIENT_EMAIL", "wzxcv123@naver.com")
    
    # Validate credentials
    if not smtp_user or not smtp_password:
        return {
            "status": "error",
            "message": "SMTP_USER or SMTP_PASSWORD not set"
        }
    
    try:
        # Create email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[경제뉴스] 일일 요약 - {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = smtp_from
        msg["To"] = recipient
        
        # Create HTML version
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px;">
                    📰 오늘의 경제뉴스 요약
                </h2>
                <p style="color: #666; font-size: 12px;">{datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    {body.replace(chr(10), '<br>')}
                </div>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 11px; color: #999;">
                    이 이메일은 자동으로 생성되었습니다. 문의사항은 관리자에게 연락하세요.
                </p>
            </body>
        </html>
        """
        
        # Attach HTML
        msg.attach(MIMEText(html, "html"))
        
        # Send email
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15.0)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15.0)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, recipient, msg.as_string())
        server.quit()
        
        return {
            "status": "success",
            "message": f"Email sent to {recipient}"
        }
    
    except smtplib.SMTPAuthenticationError:
        return {
            "status": "error",
            "message": "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD."
        }
    except smtplib.SMTPException as e:
        return {
            "status": "error",
            "message": f"SMTP error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Email send failed: {str(e)}"
        }
