import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_email_digest(summary_text):
    try:
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_from = os.getenv('SMTP_FROM', smtp_user)
        recipient = os.getenv('EMAIL_RECIPIENT', 'wzxcv123@naver.com')
        
        if not smtp_user or not smtp_password:
            return {'status': 'error', 'message': 'Missing SMTP credentials'}
        
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = recipient
        msg['Subject'] = 'Financial News Digest - Hourly Update'
        msg.attach(MIMEText(summary_text, 'plain'))
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return {'status': 'success', 'message': f'Email sent to {recipient}'}
    except smtplib.SMTPAuthenticationError:
        return {'status': 'error', 'message': 'SMTP authentication failed'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
