import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

def send_email_digest(summary_text):
    """
    Send email digest via SMTP.
    Returns dict with status and message.
    """
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM', smtp_user)
    
    if not all([smtp_user, smtp_password]):
        return {'status': 'error', 'message': 'SMTP credentials not configured'}
    
    recipient = 'wzxcv123@naver.com'
    subject = f"Financial News Digest - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Financial News Digest</h2>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <div style="line-height: 1.6;">
                {summary_text.replace(chr(10), '<br>')}
            </div>
            <hr>
            <p style="color: #666; font-size: 12px;">Automated Financial News Digest Agent</p>
        </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_from
        msg['To'] = recipient
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        return {'status': 'success', 'message': f'Email sent to {recipient}'}
    except smtplib.SMTPAuthenticationError:
        return {'status': 'error', 'message': 'SMTP authentication failed'}
    except Exception as e:
        return {'status': 'error', 'message': f'Email send failed: {str(e)}'}
