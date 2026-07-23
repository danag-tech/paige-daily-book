import re
import smtplib
import time
from email.message import EmailMessage
from html import escape
from urllib.parse import quote

from config import ConfigError, get_email_config
from subscribers import get_active_subscribers


SMTP_HOST = "smtp.163.com"
SMTP_PORT = 465
PUBLIC_SITE_BASE_URL = "https://danag-tech.github.io/paige-daily-book"
UNSUBSCRIBE_PAGE = "unsubscribe.html"


def _fallback_recipients(email_to: str) -> list[str]:
    return [
        recipient.strip()
        for recipient in email_to.replace(";", ",").split(",")
        if recipient.strip()
    ]


def _resolve_subscribers(email_to: str) -> list[dict[str, str]]:
    try:
        subscribers = get_active_subscribers()
    except Exception:
        subscribers = []

    if subscribers:
        print(f"Resolved subscriber count: {len(subscribers)}")
        print(f"Resolved recipient count: {len(subscribers)}")
        print("Resolved recipient source: Supabase")
        return subscribers

    fallback_recipients = _fallback_recipients(email_to)
    if not fallback_recipients:
        raise ConfigError("No active subscribers found and EMAIL_TO is missing.")
    print("Resolved subscriber count: 0")
    print(f"Resolved recipient count: {len(fallback_recipients)}")
    print("Resolved recipient source: fallback EMAIL_TO")
    return [{"email": recipient, "unsubscribe_token": ""} for recipient in fallback_recipients]


def _format_subject(subject: str) -> str:
    legacy_prefix = "今日荐书："
    if subject.startswith(legacy_prefix):
        theme = subject[len(legacy_prefix):].strip()
        return f"📚 今日3本精选：{theme}"
    return subject


def _build_unsubscribe_url(token: str) -> str | None:
    normalized_token = token.strip()
    if not normalized_token:
        return None
    return f"{PUBLIC_SITE_BASE_URL}/{UNSUBSCRIBE_PAGE}?token={quote(normalized_token, safe='')}"


def _append_unsubscribe_text(text_body: str, unsubscribe_url: str | None) -> str:
    if not unsubscribe_url:
        return text_body
    return (
        f"{text_body}\n\n"
        "你收到这封邮件，是因为你曾在 Paige 每日荐书网站订阅。\n"
        f"不想继续收到 Paige 每日荐书邮件？取消订阅：{unsubscribe_url}"
    )


def _append_unsubscribe_html(html_body: str, unsubscribe_url: str | None) -> str:
    if not unsubscribe_url:
        return html_body
    safe_url = escape(unsubscribe_url, quote=True)
    footer = (
        '<div style="margin-top:24px; padding-top:14px; border-top:1px solid #e5e5e5; '
        'color:#71695f; font-size:13px; line-height:1.7;">'
        '<p style="margin:0 0 6px;">你收到这封邮件，是因为你曾在 Paige 每日荐书网站订阅。</p>'
        f'<p style="margin:0;">不想继续收到 Paige 每日荐书邮件？'
        f'<a href="{safe_url}" style="color:#5f3a1e;">取消订阅</a></p>'
        '</div>'
    )
    if "</body>" in html_body:
        return html_body.replace("</body>", f"{footer}</body>", 1)
    return f"{html_body}{footer}"


def _build_message(
    subject: str,
    text_body: str,
    html_body: str | None,
    inline_images: list[dict | None] | None,
    recipient: str,
    unsubscribe_token: str,
) -> EmailMessage:
    unsubscribe_url = _build_unsubscribe_url(unsubscribe_token)
    message = EmailMessage()
    message["Subject"] = _format_subject(subject)
    message["From"] = get_email_config().email_user
    message["To"] = recipient
    if unsubscribe_url:
        message["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    message.set_content(_append_unsubscribe_text(text_body, unsubscribe_url), subtype="plain", charset="utf-8")

    if html_body is not None:
        message.add_alternative(_append_unsubscribe_html(html_body, unsubscribe_url), subtype="html", charset="utf-8")
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
    return message


def _safe_error_message(exc: Exception) -> str:
    message = str(exc)
    message = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[redacted-email]", message)
    message = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}", "[redacted-token]", message)
    return message or exc.__class__.__name__


def _mask_email(email: str) -> str:
    local_part, separator, domain = email.partition("@")
    if not separator:
        return "[invalid-email]"
    return f"{local_part[:2]}***@{domain}"


def _send_message_with_retries(message: EmailMessage) -> None:
    retry_delays = (0, 10, 30)
    for attempt, delay in enumerate(retry_delays, start=1):
        if delay:
            time.sleep(delay)
        try:
            email_config = get_email_config()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.login(email_config.email_user, email_config.email_password)
                smtp.send_message(message)
            print(f"Email sent successfully to {_mask_email(message['To'])}")
            return
        except Exception as exc:
            safe_error = _safe_error_message(exc)
            if attempt < len(retry_delays):
                print(f"Email send attempt {attempt} failed; retrying: {safe_error}")
                continue
            recipient = _mask_email(message["To"])
            print(f"Email failed for {recipient}:\n{safe_error}\nWorkflow should continue.")


def send_email(
    subject: str,
    text_body: str,
    html_body: str | None = None,
    inline_images: list[dict | None] | None = None,
) -> None:
    email_config = get_email_config()
    subscribers = _resolve_subscribers(email_config.email_to)
    print(f"Email recipient count: {len(subscribers)}")

    for subscriber in subscribers:
        message = _build_message(
            subject,
            text_body,
            html_body,
            inline_images,
            subscriber["email"],
            subscriber.get("unsubscribe_token", ""),
        )
        _send_message_with_retries(message)