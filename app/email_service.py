import logging
import smtplib
from email.message import EmailMessage

from config import settings


logger = logging.getLogger(__name__)


def _smtp_is_configured() -> bool:
    return bool(
        settings.smtp_host
        and settings.smtp_username
        and settings.smtp_password
    )


def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    subject = "Reset your ExpenseTracker password"
    text_body = (
        "We received a request to reset your password.\n\n"
        f"Use this link to set a new password:\n{reset_link}\n\n"
        "This link expires in 30 minutes. If you did not request this, ignore this email."
    )
    html_body = f"""
<html>
  <body>
    <p>We received a request to reset your password.</p>
    <p><a href="{reset_link}">Reset your password</a></p>
    <p>This link expires in 30 minutes. If you did not request this, ignore this email.</p>
  </body>
</html>
""".strip()

    if not _smtp_is_configured():
        logger.warning(
            "SMTP not configured. Password reset link for %s: %s",
            to_email,
            reset_link,
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    password = settings.smtp_password.get_secret_value() if settings.smtp_password else ""
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, password)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False


def send_verification_email(to_email: str, verify_link: str) -> bool:
    subject = "Verify your ExpenseTracker email"
    text_body = (
        "Welcome to ExpenseTracker.\n\n"
        f"Verify your email by opening this link:\n{verify_link}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    html_body = f"""
<html>
  <body>
    <p>Welcome to ExpenseTracker.</p>
    <p><a href="{verify_link}">Verify your email</a></p>
    <p>If you did not create this account, you can ignore this email.</p>
  </body>
</html>
""".strip()

    if not _smtp_is_configured():
        logger.warning(
            "SMTP not configured. Email verification link for %s: %s",
            to_email,
            verify_link,
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    password = settings.smtp_password.get_secret_value() if settings.smtp_password else ""
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username, password)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send verification email to %s", to_email)
        return False
