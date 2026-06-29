import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def send_email_summary(summary="", summary_text="", recipient="wzxcv123@naver.com", **kwargs):
    """
    Send email with summarized content via SMTP.
    Uses environment variables for secure credential storage.
    """
    try:
        # Read credentials from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)
        
        if not smtp_user or not smtp_password:
            return {"status": "error", "error_message": "SMTP credentials not configured"}
        
        # Prepare email body
        body = summary or summary_text or kwargs.get("content") or ""
        if not body:
            return {"status": "error", "error_message": "No summary content to send"}
        
        # Create email message
        msg = MIMEMultipart()
        msg["From"] = smtp_from
        msg["To"] = recipient
        msg["Subject"] = f"Bloomberg News Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Add HTML body with formatting
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2>📊 Bloomberg Daily News Summary</h2>
            <p><em>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
            <hr>
            {body.replace(chr(10), '<br>')}
            <hr>
            <p><small>This is an automated summary. Please verify important information.</small></p>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))
        
        # Send email
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15.0)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15.0)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return {"status": "success", "message": f"Email sent to {recipient}"}
    except smtplib.SMTPAuthenticationError:
        return {"status": "error", "error_message": "SMTP authentication failed"}
    except smtplib.SMTPException as e:
        return {"status": "error", "error_message": f"SMTP error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error_message": f"Email send failed: {str(e)}"}
