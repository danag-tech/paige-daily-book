import os

import requests


SUPABASE_REQUEST_TIMEOUT = 10


def get_active_subscribers() -> list[dict[str, str]]:
    """Return active subscribers with their private unsubscribe tokens."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        return []

    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/subscribers",
            params={"select": "email,unsubscribe_token", "active": "eq.true"},
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

    subscribers = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        email = row.get("email")
        token = row.get("unsubscribe_token")
        if not isinstance(email, str):
            continue
        normalized_email = email.strip().lower()
        if not normalized_email or normalized_email in seen:
            continue
        seen.add(normalized_email)
        subscribers.append({
            "email": normalized_email,
            "unsubscribe_token": str(token).strip() if token else "",
        })

    print(f"Active subscribers count: {len(subscribers)}")
    return subscribers


def get_active_subscriber_emails() -> list[str]:
    """Return active subscriber email addresses for compatibility callers."""
    return [subscriber["email"] for subscriber in get_active_subscribers()]