import json
from datetime import date
from pathlib import Path

from models import Book
from sent_books import build_book_key, build_book_keys, build_record_keys, get_cooldown_keys


BOOK_POOL_PATH = Path(__file__).with_name("data") / "book_pool.json"
MAX_BOOKS_PER_THEME = 30
MAX_BOOKS_TOTAL = 300
POOL_TARGET_TOTAL = 100
MIN_BOOKS_PER_THEME = 3
POOL_REFILL_BATCH = 20


def load_book_pool() -> list[dict]:
    if not BOOK_POOL_PATH.exists():
        return []

    with BOOK_POOL_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        return []

    return [record for record in records if isinstance(record, dict)]


def save_book_pool(records: list[dict]) -> None:
    BOOK_POOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BOOK_POOL_PATH.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")


def get_pool_health(records: list[dict], themes: list[str] | None = None) -> dict:
    if themes is None:
        config_path = Path(__file__).with_name("config.json")
        with config_path.open("r", encoding="utf-8") as file:
            themes = list(json.load(file).get("theme_strategies", {}).keys())

    theme_counts = {theme: 0 for theme in themes}
    for record in records:
        if not isinstance(record, dict):
            continue
        theme = record.get("theme")
        if theme:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

    missing_themes = [
        theme for theme in themes
        if theme_counts.get(theme, 0) < MIN_BOOKS_PER_THEME
    ]
    return {
        "total": len(records),
        "theme_counts": theme_counts,
        "missing_themes": missing_themes,
    }

def rank_pool_candidates(candidates: list[tuple[str, Book]]) -> list[tuple[str, Book]]:
    scored: list[tuple[tuple, str, Book]] = []
    seen_keys: set[str] = set()
    discovered_date = date.today().isoformat()

    for theme, book in candidates:
        keys = build_book_keys(book)
        if not keys or keys & seen_keys:
            continue
        scored.append((_record_quality_key(_book_to_record(book, theme, keys, discovered_date)), theme, book))
        seen_keys.update(keys)

    scored.sort(key=lambda item: item[0], reverse=True)
    return [(theme, book) for _, theme, book in scored]

def get_pool_books(records: list[dict], theme: str) -> list[Book]:
    books: list[Book] = []
    for record in records:
        if record.get("theme") != theme:
            continue
        book = _record_to_book(record)
        if book:
            books.append(book)
    return books


def refresh_book_pool(
    records: list[dict],
    theme: str,
    discovered_books: list[Book],
    sent_records: list[dict],
    selected_books: list[Book],
) -> list[dict]:
    blocked_keys = get_cooldown_keys(sent_records)
    for book in selected_books:
        blocked_keys.update(build_book_keys(book))

    refreshed: list[dict] = []
    existing_keys: set[str] = set()

    for record in records:
        book = _record_to_book(record)
        if not book:
            continue
        keys = _record_keys(record)
        if not keys or keys & blocked_keys or keys & existing_keys:
            continue
        refreshed.append(_normalize_record(record, book, keys))
        existing_keys.update(keys)

    today = date.today().isoformat()
    for book in discovered_books:
        keys = build_book_keys(book)
        if not keys or keys & blocked_keys or keys & existing_keys:
            continue
        refreshed.append(_book_to_record(book, theme, keys, today))
        existing_keys.update(keys)

    return _limit_pool(refreshed)


def _limit_pool(records: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for record in records:
        grouped.setdefault(record.get("theme") or "", []).append(record)

    limited_records: list[dict] = []
    for theme_records in grouped.values():
        limited_records.extend(sorted(theme_records, key=_record_quality_key, reverse=True)[:MAX_BOOKS_PER_THEME])

    return sorted(limited_records, key=_record_quality_key, reverse=True)[:MAX_BOOKS_TOTAL]


def _record_quality_key(record: dict) -> tuple:
    rating = _rating_value(record.get("rating"))
    return (
        1 if record.get("isbn") else 0,
        1 if record.get("summary") and record.get("summary") != "暂无简介" else 0,
        1 if record.get("cover") else 0,
        rating,
        record.get("discovered_date") or "",
    )


def _rating_value(rating: str | None) -> float:
    if not rating:
        return 0.0
    try:
        return float(str(rating).replace("⭐", "").strip())
    except ValueError:
        return 0.0



def _record_keys(record: dict) -> set[str]:
    return build_record_keys(record)


def _record_to_book(record: dict) -> Book | None:
    title = (record.get("title") or "").strip()
    author = (record.get("author") or "").strip()
    if not title or not author:
        return None

    return Book(
        title=title,
        author=author,
        rating=record.get("rating"),
        cover=record.get("cover"),
        summary=record.get("summary") or "暂无简介",
        source=record.get("source") or "book_pool",
        isbn=record.get("isbn"),
    )


def _normalize_record(record: dict, book: Book, keys: set[str]) -> dict:
    normalized = dict(record)
    normalized["key"] = normalized.get("key") or build_book_key(book)
    normalized["keys"] = sorted(keys)
    normalized.setdefault("discovered_date", date.today().isoformat())
    return normalized


def _book_to_record(book: Book, theme: str, keys: set[str], discovered_date: str) -> dict:
    return {
        "key": build_book_key(book),
        "keys": sorted(keys),
        "theme": theme,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "rating": book.rating,
        "cover": book.cover,
        "summary": book.summary,
        "source": book.source,
        "discovered_date": discovered_date,
    }