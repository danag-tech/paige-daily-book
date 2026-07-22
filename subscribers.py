import os

import requests


SUPABASE_REQUEST_TIMEOUT = 10


def get_active_subscriber_emails() -> list[str]:
    """Return unique, non-empty active subscriber email addresses.

    A failed or unconfigured Supabase read returns an empty list so the email
    sender can use its configured EMAIL_TO fallback.
    """
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        return []

    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/subscribers",
            params={"select": "email", "active": "eq.true"},
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
            },
            timeout=SUPABASE_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json()
    except (requests.RequestException, ValueError):
        return []

    if not isinstance(rows, list):
        return []

    emails = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        email = row.get("email")
        if not isinstance(email, str):
            continue
        normalized_email = email.strip().lower()
        if not normalized_email or normalized_email in seen:
            continue
        seen.add(normalized_email)
        emails.append(normalized_email)

    print(f"Active subscribers count: {len(emails)}")
    return emails
