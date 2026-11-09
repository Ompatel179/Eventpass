import logging

logger = logging.getLogger("eventpass")


def send_email(
    to: str,
    subject: str,
    html: str,
    attachment_name: str | None = None,
    attachment: bytes | None = None,
) -> None:
    size = len(attachment) if attachment else 0
    logger.info("Email ready (no provider, not sent): %s, attachment %d bytes", subject, size)


def get_email_sender():
    return send_email