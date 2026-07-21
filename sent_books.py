import json
import re
from datetime import date
from pathlib import Path


SENT_BOOKS_PATH = Path(__file__).with_name("sent_books.json")


def load_sent_books() -> list[dict]:
    if not SENT_BOOKS_PATH.exists():
        return []

    with SENT_BOOKS_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        return []

    return records


def save_sent_books(records: list[dict]) -> None:
    with SENT_BOOKS_PATH.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")


def build_book_key(book) -> str:
    keys = build_book_keys(book)
    if book.isbn:
        return next(key for key in keys if key.startswith("isbn:"))
    return next(iter(keys))


def build_book_keys(book) -> set[str]:
    keys: set[str] = set()

    if book.isbn:
        normalized_isbn = _normalize_isbn(book.isbn)
        if normalized_isbn:
            keys.add(f"isbn:{normalized_isbn}")

    title_author_key = build_title_author_key(book.title, book.author)
    if title_author_key:
        keys.add(title_author_key)

    return keys


def build_record_keys(record: dict) -> set[str]:
    keys = {key for key in record.get("keys", []) if isinstance(key, str) and key}

    key = record.get("key")
    if isinstance(key, str) and key:
        keys.add(key)

    isbn = record.get("isbn")
    if isinstance(isbn, str) and isbn.strip():
        normalized_isbn = _normalize_isbn(isbn)
        if normalized_isbn:
            keys.add(f"isbn:{normalized_isbn}")

    title_author_key = build_title_author_key(record.get("title") or "", record.get("author") or "")
    if title_author_key:
        keys.add(title_author_key)

    return keys


def build_title_author_key(title: str, author: str) -> str | None:
    normalized_title = _normalize_title(title)
    normalized_author = _normalize_author(author)
    if not normalized_title or not normalized_author:
        return None
    return f"title_author:{normalized_title}|{normalized_author}"


def filter_unsent_books(books: list, sent_records: list[dict]) -> list:
    sent_keys = _records_keys(sent_records)
    return [book for book in books if build_book_keys(book).isdisjoint(sent_keys)]


def append_sent_books(records: list[dict], books: list, theme: str) -> list[dict]:
    existing_keys = _records_keys(records)
    updated_records = list(records)
    sent_date = date.today().isoformat()

    for book in books:
        keys = build_book_keys(book)
        if not keys or not keys.isdisjoint(existing_keys):
            continue

        primary_key = build_book_key(book)
        updated_records.append(
            {
                "key": primary_key,
                "keys": sorted(keys),
                "title": book.title,
                "author": book.author,
                "isbn": book.isbn,
                "theme": theme,
                "rating": book.rating,
                "cover": book.cover,
                "summary": book.summary,
                "source": book.source,
                "sent_date": sent_date,
            }
        )
        existing_keys.update(keys)

    return updated_records


def _records_keys(records: list[dict]) -> set[str]:
    keys: set[str] = set()
    for record in records:
        if isinstance(record, dict):
            keys.update(build_record_keys(record))
    return keys


def _normalize_isbn(isbn: str) -> str:
    return re.sub(r"[\s-]+", "", isbn).lower()


def _normalize_title(title: str) -> str:
    return "".join(title.strip().replace("《", "").replace("》", "").split()).lower()


def _normalize_author(author: str) -> str:
    return "".join(author.strip().split()).lower()