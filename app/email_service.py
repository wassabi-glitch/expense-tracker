import logging
import smtplib
import json
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from email.message import EmailMessage

from config import settings

logger = logging.getLogger(__name__)

# --- PREMIUM EMAIL STYLES ---
PRIMARY_COLOR = "#22c55e"  # Sarflog Green
BG_COLOR = "#f4f4f4"
WHITE = "#ffffff"

def _get_base_template(content_html: str, action_text: str, action_url: str) -> str:
    """Provides a consistent, premium wrap for all outgoing emails."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: {BG_COLOR}; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 40px auto; background-color: {WHITE}; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
        .header {{ background-color: {PRIMARY_COLOR}; padding: 30px; text-align: center; color: white; }}
        .content {{ padding: 40px; line-height: 1.6; color: #374151; }}
        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #9ca3af; }}
        .button-container {{ text-align: center; margin-top: 30px; }}
        .button {{ background-color: {PRIMARY_COLOR}; color: white !important; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block; }}
        h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
        p {{ margin: 0 0 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Sarflog</h1>
        </div>
        <div class="content">
            {content_html}
            <div class="button-container">
                <a href="{action_url}" class="button">{action_text}</a>
            </div>
        </div>
        <div class="footer">
            &copy; 2024 Sarflog. All rights reserved.<br>
            Sent via <strong>staging-mail.sarflog.uz</strong>
        </div>
    </div>
</body>
</html>
""".strip()

def _send_email(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
    """Centralized, resilient email sender helper.

    Delivery order:
    1) Resend HTTP API (if RESEND_API_KEY is set)
    2) SMTP fallback
    """
    if _send_email_via_resend_api(to_email, subject, text_body, html_body):
        return True
    return _send_email_via_smtp(to_email, subject, text_body, html_body)


def _send_email_via_resend_api(
    to_email: str, subject: str, text_body: str, html_body: str
) -> bool:
    api_key = settings.resend_api_key
    if not api_key:
        return False

    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }
    body = json.dumps(payload).encode("utf-8")
    endpoint = "https://api.resend.com/emails"
    req = Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=20) as resp:
            status_code = getattr(resp, "status", None)
            if status_code and status_code >= 400:
                logger.error("Resend API returned status=%s for %s", status_code, to_email)
                return False
        return True
    except HTTPError as exc:
        logger.exception("Resend API HTTP error for %s: status=%s", to_email, exc.code)
        return False
    except URLError:
        logger.exception("Resend API network error for %s", to_email)
        return False
    except Exception:
        logger.exception("Unexpected Resend API send failure for %s", to_email)
        return False


def _send_email_via_smtp(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
    if not settings.smtp_host or not settings.smtp_password:
        logger.warning("SMTP not configured. Missing Host or Password. Host=%s", settings.smtp_host)
        return False

    logger.info("Email Attempt: Connecting to %s:%s", settings.smtp_host, settings.smtp_port)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    pwd = settings.smtp_password.get_secret_value()
    try:
        # We use a short timeout (20s) to avoid hanging the app.
        if settings.smtp_port == 465:
            server_class = smtplib.SMTP_SSL
        else:
            server_class = smtplib.SMTP

        with server_class(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_port != 465 and settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_username or "resend", pwd)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False

def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    subject = "Reset your Sarflog password"
    text_body = f"Use this link to set a new password: {reset_link}\nThis link expires in 30 minutes."
    
    content_html = """
        <p>Hello,</p>
        <p>We received a request to reset your password. If you didn't make this request, you can safely ignore this email.</p>
        <p>Ready to set a new password? Click the button below:</p>
    """
    html_body = _get_base_template(content_html, "Reset Password", reset_link)
    return _send_email(to_email, subject, text_body, html_body)

def send_verification_email(to_email: str, verify_link: str) -> bool:
    subject = "Verify your Sarflog email"
    text_body = f"Welcome to Sarflog! Verify your email by opening this link: {verify_link}"
    
    content_html = """
        <p>Welcome to <strong>Sarflog</strong>!</p>
        <p>To finish setting up your account and start tracking your finances like a pro, please verify your email address.</p>
    """
    html_body = _get_base_template(content_html, "Verify Email", verify_link)
    return _send_email(to_email, subject, text_body, html_body)
