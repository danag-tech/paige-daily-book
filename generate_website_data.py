import hashlib
import json
import re

import requests
from pathlib import Path
from urllib.parse import quote, urlparse

from book_pool import load_book_pool
from cover_image import COVER_HEADERS, _detect_image_subtype, build_placeholder_cover_png
from sent_books import build_record_keys, load_sent_books


PUBLIC_BOOK_LIMIT = 15
TODAY_BOOK_LIMIT = 3
WEBSITE_DIR = Path(__file__).with_name("website")
WEBSITE_BOOKS_PATH = WEBSITE_DIR / "books.json"
WEBSITE_TODAY_PATH = WEBSITE_DIR / "today.json"
WEBSITE_COVERS_DIR = WEBSITE_DIR / "covers"
PUBLIC_SITE_BASE_URL = "https://danag-tech.github.io/paige-daily-book"
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
PROMOTIONAL_LINE_PATTERN = re.compile(r"^(❖.*?❖|[★☆·•◌⋄]+|【?内容简介】?|【?媒体推荐】?|【?学人推荐】?|编辑推荐[:：]?|推荐语[:：]?)")
MARKDOWN_PREFIX_PATTERN = re.compile(r"^\s{0,3}(#{1,6}\s+|[-*+]\s+|>\s*|\d+[.)]\s+)")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]*\)")
PROMOTIONAL_PHRASES = (
    "❖编辑推荐❖",
    "编辑推荐：",
    "编辑推荐:",
    "强烈推荐",
    "重磅推荐",
    "必读佳作",
    "值得一读",
    "不可错过",
    "诚意推荐",
    "推荐阅读",
)


def generate_website_books(records: list[dict] | None = None, limit: int = PUBLIC_BOOK_LIMIT) -> list[dict]:
    source_records = records if records is not None else load_sent_books()
    supplement_lookup = {} if records is not None else _build_supplement_lookup(load_book_pool())
    normalized_records = _normalize_records(source_records, supplement_lookup)
    return _select_public_books(normalized_records, limit)


def generate_today_books(records: list[dict] | None = None, limit: int = TODAY_BOOK_LIMIT) -> list[dict]:
    source_records = records if records is not None else load_sent_books()
    supplement_lookup = {} if records is not None else _build_supplement_lookup(load_book_pool())
    normalized_records = _normalize_records(source_records, supplement_lookup)
    if not normalized_records:
        return []

    latest_date = normalized_records[0][0]
    latest_records = [item for item in normalized_records if item[0] == latest_date]
    return _select_public_books(latest_records, limit)


def save_website_books(books: list[dict], today_books: list[dict] | None = None) -> None:
    WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
    public_books = _with_public_cover_assets(books[:PUBLIC_BOOK_LIMIT])
    current_today_books = today_books if today_books is not None else public_books[:TODAY_BOOK_LIMIT]
    public_today_books = _with_public_cover_assets(current_today_books[:TODAY_BOOK_LIMIT])

    with WEBSITE_BOOKS_PATH.open("w", encoding="utf-8") as file:
        json.dump(public_books, file, ensure_ascii=False, indent=2)
        file.write("\n")

    with WEBSITE_TODAY_PATH.open("w", encoding="utf-8") as file:
        json.dump(public_today_books, file, ensure_ascii=False, indent=2)
        file.write("\n")


def update_website_books() -> list[dict]:
    books = generate_website_books()
    today_books = generate_today_books()
    save_website_books(books, today_books)
    print(f"Website books updated: {len(books)} books, {len(today_books)} today books")
    return books


def _normalize_records(records: list[dict], supplement_lookup: dict[str, dict] | None = None) -> list[tuple[str, int, dict, dict]]:
    normalized_records = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        public_record = _to_public_record(_merge_supplement(record, supplement_lookup or {}))
        if public_record:
            normalized_records.append((record.get("sent_date") or "", index, record, public_record))

    normalized_records.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return normalized_records


def _build_supplement_lookup(records: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        for key in build_record_keys(record):
            lookup.setdefault(key, record)
    return lookup


def _merge_supplement(record: dict, supplement_lookup: dict[str, dict]) -> dict:
    if not supplement_lookup:
        return record

    supplement = None
    for key in build_record_keys(record):
        supplement = supplement_lookup.get(key)
        if supplement:
            break

    if not supplement:
        return record

    merged = dict(record)
    for field in ("rating", "cover", "summary", "weread_url"):
        if not merged.get(field) and supplement.get(field):
            merged[field] = supplement[field]
    return merged



def _with_public_cover_assets(books: list[dict]) -> list[dict]:
    WEBSITE_COVERS_DIR.mkdir(parents=True, exist_ok=True)
    public_books = []
    for book in books:
        public_book = dict(book)
        public_book["cover"] = _build_public_cover_asset(public_book)
        public_books.append(public_book)
    return public_books


def _build_public_cover_asset(book: dict) -> str:
    title = _clean_text(book.get("title")) or "book"
    author = _clean_text(book.get("author"))
    base_name = hashlib.sha1(f"{title}|{author}".encode("utf-8")).hexdigest()[:16]
    cover_url = _safe_public_url(book.get("cover"))
    if cover_url:
        image = _download_cover_asset(cover_url)
        if image:
            filename = f"{base_name}.{image['subtype']}"
            (WEBSITE_COVERS_DIR / filename).write_bytes(image["image_bytes"])
            return f"{PUBLIC_SITE_BASE_URL}/covers/{filename}"

    filename = f"{base_name}.png"
    (WEBSITE_COVERS_DIR / filename).write_bytes(build_placeholder_cover_png(title, author))
    return f"{PUBLIC_SITE_BASE_URL}/covers/{filename}"


def _download_cover_asset(url: str) -> dict | None:
    try:
        response = requests.get(url, headers=COVER_HEADERS, timeout=15)
    except requests.RequestException:
        return None

    if response.status_code != 200 or not response.content:
        return None

    subtype = _detect_image_subtype(response.headers.get("Content-Type", ""), response.content)
    if not subtype or len(response.content) < 1000:
        return None
    if subtype == "jpeg":
        subtype = "jpg"
    return {"image_bytes": response.content, "subtype": subtype}


def _select_public_books(normalized_records: list[tuple[str, int, dict, dict]], limit: int) -> list[dict]:
    books = []
    seen_history_keys: set[str] = set()
    for _, _, original_record, public_record in normalized_records:
        book_keys = build_record_keys(original_record) or {_fallback_key(public_record)}
        sent_date = _clean_text(original_record.get("sent_date"))
        history_keys = {f"{sent_date}|{book_key}" for book_key in book_keys}
        if history_keys & seen_history_keys:
            continue
        if _contains_sensitive_value(public_record):
            continue
        selected_record = dict(public_record)
        selected_record["detail_url"] = f"book.html?id={len(books)}"
        books.append(selected_record)
        seen_history_keys.update(history_keys)
        if len(books) >= limit:
            break

    return books

def _to_public_record(record: dict) -> dict | None:
    title = _clean_text(record.get("title"))
    if not title:
        return None
    isbn = _clean_text(record.get("isbn"))

    return {
        "title": title,
        "author": _clean_text(record.get("author")) or "暂无作者",
        "rating": _clean_text(record.get("rating")) or "暂无评分",
        "cover": _resolve_cover(record, isbn, title),
        "summary": _clean_summary(record.get("summary")) or "暂无简介",
        "recommended_date": _clean_text(record.get("sent_date")) or "暂无日期",
        "detail_url": "",
        "weread_url": _resolve_weread_url(record, title),
    }


def _clean_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return " ".join(text.split())


def _clean_summary(value) -> str:
    if value is None:
        return ""

    kept_lines = []
    for raw_line in str(value).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if PROMOTIONAL_LINE_PATTERN.match(line):
            continue
        line = MARKDOWN_PREFIX_PATTERN.sub("", line)
        line = MARKDOWN_LINK_PATTERN.sub(r"\1", line)
        line = line.replace("**", "").replace("__", "").replace("`", "")
        line = line.replace("---", "").replace("###", "").replace("##", "").replace("#", "")
        for phrase in PROMOTIONAL_PHRASES:
            line = line.replace(phrase, "")
        line = line.strip(" -—*_:：[]()（）")
        if line:
            kept_lines.append(line)

    return " ".join(" ".join(kept_lines).split())


def _safe_public_url(value) -> str | None:
    url = _clean_text(value)
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return None



def _resolve_cover(record: dict, isbn: str, title: str) -> str | None:
    cover = _safe_public_url(record.get("cover"))
    if cover:
        return cover
    if isbn:
        return f"https://covers.openlibrary.org/b/isbn/{_url_encode(isbn)}-L.jpg"
    if cover:
        return _normalize_cover_url(cover)
    return _find_cover_by_title(title)


def _find_cover_by_title(title: str) -> str | None:
    if not title:
        return None

    try:
        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": f"intitle:{title}", "langRestrict": "zh", "maxResults": 5},
            timeout=10,
        )
        response.raise_for_status()
        items = response.json().get("items") or []
    except (requests.RequestException, ValueError):
        return None

    for item in items:
        volume_info = item.get("volumeInfo") or {}
        image_links = volume_info.get("imageLinks") or {}
        cover = _safe_public_url(image_links.get("thumbnail") or image_links.get("smallThumbnail"))
        if cover:
            return _normalize_cover_url(cover)
    return None



def _is_douban_cover(url: str) -> bool:
    return urlparse(url).netloc.endswith("doubanio.com")

def _normalize_cover_url(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.netloc.endswith("doubanio.com"):
        source_url = url
        if parsed_url.query:
            source_url = f"{source_url}?{parsed_url.query}"
        return f"https://images.weserv.nl/?url={_url_encode(source_url)}"
    return url.replace("http://", "https://", 1)


def _url_encode(value: str) -> str:
    return quote(value, safe="")

def _resolve_weread_url(record: dict, title: str) -> str:
    weread_url = _safe_public_url(record.get("weread_url"))
    if weread_url:
        return weread_url
    return f"https://weread.qq.com/web/search/books?keyword={_url_encode(title)}"

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
