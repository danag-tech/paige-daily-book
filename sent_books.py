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
    if book.isbn:
        normalized_isbn = re.sub(r"[\s-]+", "", book.isbn).lower()
        return f"isbn:{normalized_isbn}"

    return f"title_author:{_normalize_title(book.title)}|{_normalize_author(book.author)}"


def filter_unsent_books(books: list, sent_records: list[dict]) -> list:
    sent_keys = {record.get("key") for record in sent_records if record.get("key")}
    return [book for book in books if build_book_key(book) not in sent_keys]


def append_sent_books(records: list[dict], books: list, theme: str) -> list[dict]:
    existing_keys = {record.get("key") for record in records if record.get("key")}
    updated_records = list(records)
    sent_date = date.today().isoformat()

    for book in books:
        key = build_book_key(book)
        if key in existing_keys:
            continue

        updated_records.append(
            {
                "key": key,
                "title": book.title,
                "author": book.author,
                "isbn": book.isbn,
                "theme": theme,
                "sent_date": sent_date,
            }
        )
        existing_keys.add(key)

    return updated_records


def _normalize_title(title: str) -> str:
    return "".join(title.strip().replace("《", "").replace("》", "").split()).lower()


def _normalize_author(author: str) -> str:
    return "".join(author.strip().split()).lower()
