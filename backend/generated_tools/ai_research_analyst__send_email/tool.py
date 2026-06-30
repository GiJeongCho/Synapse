import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(summary="", summary_text="", content="", **kwargs):
    body = summary or summary_text or content or kwargs.get("digest") or ""
    if not body:
        return {"status": "error", "message": "No content to send"}
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    pw = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", user)
    recipient = kwargs.get("recipient") or os.getenv("RECIPIENT_EMAIL") or ''
    if not user or not pw:
        return {"status": "error", "message": "SMTP credentials not configured"}
    if not recipient:
        return {"status": "error", "message": "No recipient configured"}
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = 'AI Research Analyst and Technical Writer specializing in art'
    msg.attach(MIMEText(body, "plain"))
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=20)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            server.starttls()
        server.login(user, pw)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        return {"status": "error", "message": "Email send failed: " + str(e)}
    return {"status": "success", "message": "Email sent to " + recipient}
