import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
import re

logger = logging.getLogger(__name__)

def send_digest_email(summary):
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM', smtp_user)
    recipient = os.getenv('RECIPIENT_EMAIL', 'wzxcv123@naver.com')
    
    if not all([smtp_user, smtp_password]):
        return {'status': 'error', 'message': 'SMTP credentials not configured'}
    
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, recipient):
        return {'status': 'error', 'message': f'Invalid recipient email: {recipient}'}
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Financial News Digest - Hourly Update'
        msg['From'] = smtp_from
        msg['To'] = recipient
        
        html = f'''<html><body>
        <h2>Financial News Digest</h2>
        <p>{summary}</p>
        <hr>
        <p><small>Automated digest generated hourly</small></p>
        </body></html>'''
        
        msg.attach(MIMEText(html, 'html'))
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f'Email sent to {recipient}')
        return {'status': 'success', 'message': f'Email sent to {recipient}'}
    except Exception as e:
        logger.error(f'Email send error: {e}')
        return {'status': 'error', 'message': str(e)}
