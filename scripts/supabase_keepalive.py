import base64
import json
import os
import sys

import requests


SUPABASE_REQUEST_TIMEOUT = 10


def _decode_legacy_role(key: str) -> str:
    parts = key.split(".")
    if len(parts) != 3:
        return ""
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    role = claims.get("role")
    return role if isinstance(role, str) else ""


def _get_low_privilege_key() -> tuple[str, str]:
    key = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )
    if not key:
        raise RuntimeError("No low-privilege Supabase key is configured")
    if key.startswith("sb_publishable_"):
        return key, "publishable"
    if key.startswith("sb_secret_"):
        raise RuntimeError("Supabase secret keys are forbidden for keepalive")

    role = _decode_legacy_role(key)
    if role == "anon":
        return key, "legacy anon"
    if role == "service_role":
        raise RuntimeError("Supabase service_role JWTs are forbidden for keepalive")
    raise RuntimeError("Configured Supabase key is not a confirmed low-privilege key")


def keepalive() -> None:
    """Perform one minimal read-only query against the dedicated keepalive table."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is missing")

    supabase_key, key_type = _get_low_privilege_key()
    headers = {"apikey": supabase_key}
    if key_type == "legacy anon":
        headers["Authorization"] = f"Bearer {supabase_key}"

    print(f"Using low-privilege Supabase key: {key_type}")
    response = requests.get(
        f"{supabase_url}/rest/v1/keepalive",
        params={"select": "id,status", "id": "eq.1", "limit": "1"},
        headers=headers,
        timeout=SUPABASE_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows or rows[0].get("id") != 1:
        raise RuntimeError("Supabase keepalive response did not contain id=1")
    print("Supabase keepalive succeeded")


def main() -> None:
    try:
        keepalive()
    except Exception as exc:
        print(f"Supabase keepalive failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
