import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_email_digest(summary="", summary_text="", **kwargs):
    try:
        body = summary or summary_text or kwargs.get('content') or ''
        if not body:
            return {'status': 'error'}
        
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        smtp_from = os.getenv('SMTP_FROM', smtp_user)
        recipient = 'wzxcv123@naver.com'
        
        if not smtp_user or not smtp_password:
            return {'status': 'error'}
        
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = recipient
        msg['Subject'] = 'Bloomberg Daily News Digest'
        msg.attach(MIMEText(body, 'plain'))
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error'}
