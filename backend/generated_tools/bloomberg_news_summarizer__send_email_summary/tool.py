import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def send_email_summary(summary_text="", subject=""):
    """SMTP로 요약 메일을 발송한다."""
    try:
        smtp_server = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        sender_email = os.getenv("SMTP_USER", "")
        sender_password = os.getenv("SMTP_PASSWORD", "")
        sender_from = os.getenv("SMTP_FROM", sender_email)
        recipient = "wzxcv123@naver.com"

        if not sender_email or not sender_password:
            return {"status": "error", "message": "SMTP_USER / SMTP_PASSWORD 환경변수 누락"}

        if not subject:
            subject = f"Bloomberg News Summary - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        if not summary_text:
            summary_text = "(요약 내용 없음)"

        msg = MIMEMultipart()
        msg["From"] = sender_from
        msg["To"] = recipient
        msg["Subject"] = subject

        body = f"Daily Bloomberg News Summary\n{'='*40}\n\n{summary_text}\n\nGenerated at {datetime.now()}"
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

        logger.info("Email sent to %s", recipient)
        return {"status": "success", "recipient": recipient, "timestamp": datetime.now().isoformat()}

    except smtplib.SMTPAuthenticationError:
        return {"status": "auth_error", "message": "SMTP 인증 실패 — Gmail은 앱 비밀번호 필요 (2단계 인증 → 앱 비밀번호 생성)"}
    except smtplib.SMTPException as e:
        return {"status": "smtp_error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
