import smtplib
from email.message import EmailMessage

from config import get_email_config


SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465


def send_email(subject: str, body: str) -> None:
    email_config = get_email_config()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = email_config.email_user
    message["To"] = email_config.email_to
    message.set_content(body, subtype="plain", charset="utf-8")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(email_config.email_user, email_config.email_password)
        smtp.send_message(message)
