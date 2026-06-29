import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def email_dispatcher(summary="", summary_text="", **kwargs):
    """
    Send summarized news via email.
    Reads summary from either 'summary' or 'summary_text' parameter.
    Uses SMTP with environment variable credentials.
    """
    try:
        # Get email configuration from environment
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_from = os.getenv('SMTP_FROM', smtp_user)
        
        # Validate credentials
        if not smtp_user or not smtp_password:
            logger.error('SMTP credentials not configured')
            return {
                'status': 'error',
                'message': 'SMTP_USER and SMTP_PASSWORD environment variables required'
            }
        
        # Get recipient and subject
        recipient = kwargs.get('recipient') or 'wzxcv123@naver.com'
        subject = kwargs.get('subject') or f"[네이버 경제뉴스] 일일 요약 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Get email body
        body = summary or summary_text or kwargs.get('content') or ''
        if not body:
            logger.warning('No content to send')
            return {
                'status': 'error',
                'message': 'No summary content provided'
            }
        
        # Create HTML email
        html_content = _create_html_email(body)
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_from
        msg['To'] = recipient
        
        # Attach plain text and HTML versions
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Send email
        if smtp_port == 465:
            # Use SSL
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15.0)
        else:
            # Use TLS
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15.0)
            server.starttls()
        
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, recipient, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent successfully to {recipient}")
        return {
            'status': 'success',
            'message': f'Email sent to {recipient}'
        }
    
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {str(e)}")
        return {
            'status': 'error',
            'message': f'SMTP authentication failed: {str(e)}'
        }
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        return {
            'status': 'error',
            'message': f'SMTP error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Email dispatch error: {str(e)}")
        return {
            'status': 'error',
            'message': f'Email dispatch failed: {str(e)}'
        }

def _create_html_email(body):
    """
    Create HTML-formatted email with CSS styling.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                border-bottom: 3px solid #1e88e5;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                color: #1e88e5;
                margin: 0;
                font-size: 24px;
            }}
            .timestamp {{
                color: #999;
                font-size: 12px;
                margin-top: 5px;
            }}
            .content {{
                white-space: pre-wrap;
                word-wrap: break-word;
                background-color: #f9f9f9;
                padding: 15px;
                border-left: 4px solid #1e88e5;
                border-radius: 4px;
                font-size: 14px;
                line-height: 1.8;
            }}
            .footer {{
                margin-top: 20px;
                padding-top: 15px;
                border-top: 1px solid #eee;
                color: #999;
                font-size: 12px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📰 네이버 경제뉴스 일일 요약</h1>
                <div class="timestamp">{datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</div>
            </div>
            <div class="content">
{body}
            </div>
            <div class="footer">
                <p>이 이메일은 자동으로 생성되었습니다. 회신하지 마세요.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html
