import os
import sys

import requests


SUPABASE_REQUEST_TIMEOUT = 10


def keepalive() -> None:
    """Perform one minimal read-only query against the subscribers table."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL is missing")
    if not supabase_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY is missing")

    response = requests.get(
        f"{supabase_url}/rest/v1/subscribers",
        params={"select": "email", "limit": "1"},
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
        },
        timeout=SUPABASE_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    print("Supabase keepalive succeeded")


def main() -> None:
    try:
        keepalive()
    except Exception as exc:
        print(f"Supabase keepalive failed: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
