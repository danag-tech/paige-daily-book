import smtplib
from email.message import EmailMessage

from config import get_email_config


SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465


def send_email(
    subject: str,
    text_body: str,
    html_body: str | None = None,
    inline_images: list[dict | None] | None = None,
) -> None:
    email_config = get_email_config()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_config.email_user
    message["To"] = email_config.email_to
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
