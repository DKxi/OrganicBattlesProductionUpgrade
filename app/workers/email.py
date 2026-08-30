import logging
from typing import Optional
from app.infrastructure.messaging.smtp import send_verification_code_email

logger = logging.getLogger("organicbattles.workers")


def process_verification_email_task(to_email: str, username: str, code: str) -> bool:
    """Worker task to send verification email asynchronously."""
    logger.info("Executing async email task for %s", to_email)
    return send_verification_code_email(to_email, username, code)
