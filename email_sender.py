import smtplib
from email.message import EmailMessage

from config import ConfigError, get_email_config
from subscribers import get_active_subscriber_emails


SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465


def _fallback_recipients(email_to: str) -> list[str]:
    return [
        recipient.strip()
        for recipient in email_to.replace(";", ",").split(",")
        if recipient.strip()
    ]


def _resolve_recipients(email_to: str) -> list[str]:
    try:
        subscriber_emails = get_active_subscriber_emails()
    except Exception:
        subscriber_emails = []

    if subscriber_emails:
        return subscriber_emails

    fallback_recipients = _fallback_recipients(email_to)
    if not fallback_recipients:
        raise ConfigError("No active subscribers found and EMAIL_TO is missing.")
    return fallback_recipients


def send_email(
    subject: str,
    text_body: str,
    html_body: str | None = None,
    inline_images: list[dict | None] | None = None,
) -> None:
    email_config = get_email_config()
    recipients = _resolve_recipients(email_config.email_to)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_config.email_user
    message["To"] = ", ".join(recipients)
    message.set_content(text_body, subtype="plain", charset="utf-8")

    if html_body is not None:
        message.add_alternative(html_body, subtype="html", charset="utf-8")
        html_part = message.get_payload()[-1]
        for image in inline_images or []:
            if not image:
                continue
            html_part.add_related(
                image["image_bytes"],
                maintype=image["maintype"],
                subtype=image["subtype"],
                cid=f"<{image['cid']}>",
            )

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(email_config.email_user, email_config.email_password)
        smtp.send_message(message)
