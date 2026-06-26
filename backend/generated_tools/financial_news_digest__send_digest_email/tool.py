import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_digest_email(summary_text):
    try:
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_from = os.getenv('SMTP_FROM', smtp_user)
        
        if not smtp_user or not smtp_password:
            return {'status': 'error', 'message': 'SMTP credentials missing'}
        
        recipient = 'wzxcv123@naver.com'
        
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = recipient
        msg['Subject'] = 'Financial News Digest - Hourly Update'
        
        body = f"{summary_text}\n\n---\nSent by Financial News Digest Agent"
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        return {'status': 'success', 'message': f'Email sent to {recipient}'}
    except smtplib.SMTPAuthenticationError:
        return {'status': 'error', 'message': 'SMTP authentication failed'}
    except Exception as e:
        return {'status': 'error', 'message': f'Email send failed: {str(e)}'}
