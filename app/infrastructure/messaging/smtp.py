import logging
import smtplib
from email.message import EmailMessage
from typing import Optional
from app.settings import settings

logger = logging.getLogger("organicbattles.messaging")


def send_email_message(to_email: str, subject: str, body: str) -> bool:
    """Send transactional email via SMTP with STARTTLS or fallback to console."""
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        logger.info("[MESSAGING (CONSOLE)] %s -> %s\n%s", subject, to_email, body)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_username
    message["To"] = to_email
    message.set_content(body)

    smtp_password = settings.smtp_password.replace(" ", "") if settings.smtp_password else ""

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(settings.smtp_username, smtp_password)
            server.send_message(message)
        logger.info("Sent email '%s' to %s", subject, to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s via SMTP (%s): %s", to_email, settings.smtp_host, exc)
        logger.info("[MESSAGING FALLBACK (CONSOLE)] %s -> %s\n%s", subject, to_email, body)
        return False


def send_verification_code_email(to_email: str, username: str, code: str) -> bool:
    """Send verification OTP email."""
    subject = f"Your {settings.project_name} confirmation code: {code}"
    body = (
        f"Hello {username},\n\n"
        f"Your verification code for {settings.project_name} is:\n\n"
        f"  {code}\n\n"
        f"This code will expire in {settings.verification_code_ttl_seconds // 60} minutes.\n"
        "If you did not request this, you can safely ignore this message.\n"
    )
    return send_email_message(to_email, subject, body)
