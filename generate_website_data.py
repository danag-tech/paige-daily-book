import json
import re
from pathlib import Path

from sent_books import build_record_keys, load_sent_books


PUBLIC_BOOK_LIMIT = 15
WEBSITE_DIR = Path(__file__).with_name("website")
WEBSITE_BOOKS_PATH = WEBSITE_DIR / "books.json"
LOCAL_PATH_PATTERN = re.compile(r"([A-Za-z]:\\|/home/|/Users/|\\\\)")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_FIELD_NAMES = {
    "key",
    "keys",
    "isbn",
    "source",
    "theme",
    "email",
    "password",
    "token",
    "secret",
    "api_key",
}


def generate_website_books(records: list[dict] | None = None, limit: int = PUBLIC_BOOK_LIMIT) -> list[dict]:
    source_records = records if records is not None else load_sent_books()
    normalized_records = []

    for index, record in enumerate(source_records):
        if not isinstance(record, dict):
            continue
        public_record = _to_public_record(record)
        if public_record:
            normalized_records.append((record.get("sent_date") or "", index, record, public_record))

    normalized_records.sort(key=lambda item: (item[0], item[1]), reverse=True)

    books = []
    seen_keys: set[str] = set()
    for _, _, original_record, public_record in normalized_records:
        duplicate_keys = build_record_keys(original_record) or {_fallback_key(public_record)}
        if duplicate_keys & seen_keys:
            continue
        if _contains_sensitive_value(public_record):
            continue
        books.append(public_record)
        seen_keys.update(duplicate_keys)
        if len(books) >= limit:
            break

    return books


def save_website_books(books: list[dict]) -> None:
    WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
    with WEBSITE_BOOKS_PATH.open("w", encoding="utf-8") as file:
        json.dump(books[:PUBLIC_BOOK_LIMIT], file, ensure_ascii=False, indent=2)
        file.write("\n")


def update_website_books() -> list[dict]:
    books = generate_website_books()
    save_website_books(books)
    print(f"Website books updated: {len(books)} books")
    return books


def _to_public_record(record: dict) -> dict | None:
    title = _clean_text(record.get("title"))
    if not title:
        return None

    return {
        "title": title,
        "author": _clean_text(record.get("author")) or "暂无作者",
        "rating": _clean_text(record.get("rating")) or "暂无评分",
        "cover": _safe_cover_url(record.get("cover")),
        "summary": _clean_text(record.get("summary")) or "暂无简介",
        "recommended_date": _clean_text(record.get("sent_date")) or "暂无日期",
    }


def _clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return " ".join(text.split())


def _safe_cover_url(value) -> str | None:
    url = _clean_text(value)
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return None


def _fallback_key(record: dict) -> str:
    return f"{record.get('title', '')}|{record.get('author', '')}".lower()


def _contains_sensitive_value(record: dict) -> bool:
    for key, value in record.items():
        if key in SECRET_FIELD_NAMES:
            return True
        if not isinstance(value, str):
            continue
        lowered_value = value.lower()
        if EMAIL_PATTERN.search(value) or LOCAL_PATH_PATTERN.search(value):
            return True
        if any(marker in lowered_value for marker in ("api_key", "password", "token", "secret")):
            return True
    return False


if __name__ == "__main__":
    update_website_books()