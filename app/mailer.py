import logging
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage

log = logging.getLogger("app.mailer")


def send_email(to, subject, body):
    """Send a plain-text email. Returns True if it was sent (or printed), False if sending failed.

    Settings come from .env: SMTP_HOST, SMTP_PORT (default 587), SMTP_USERNAME,
    SMTP_PASSWORD and MAIL_FROM. If SMTP_HOST is not set, nothing is sent and the
    email is printed in the Flask terminal instead, so development works without
    a mail account.
    """
    host = os.getenv("SMTP_HOST")
    if not host:
        log.warning(
            "SMTP is not configured, so this email was NOT sent.\nTo: %s\nSubject: %s\n\n%s",
            to, subject, body,
        )
        return True

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    message = EmailMessage()
    message["From"] = os.getenv("MAIL_FROM") or username or "no-reply@localhost"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        context = ssl.create_default_context()
        if port == 465:  # connection is encrypted from the start
            server = smtplib.SMTP_SSL(host, port, context=context, timeout=15)
        else:  # normally 587: connect, then switch to an encrypted connection
            server = smtplib.SMTP(host, port, timeout=15)
        with server:
            if port != 465:
                server.starttls(context=context)
            if username:
                server.login(username, password or "")
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        log.exception("Could not send email to %s", to)
        return False
    return True


def send_email_async(to, subject, body):
    """Send in the background, so the page answers just as fast whether or not an email goes out."""
    threading.Thread(target=send_email, args=(to, subject, body), daemon=True).start()
