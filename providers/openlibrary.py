import requests

from models import Book
from providers.base import BookProvider


MIN_CHINESE_RATIO = 0.08
CHINESE_LANGUAGE_CODES = {"chi", "zho", "zh", "zh-cn", "zh-tw"}


class OpenLibraryProvider(BookProvider):
    name = "openlibrary"
    source_label = "Open Library"

    def __init__(self, timeout: int = 8, theme_strategies: dict[str, dict] | None = None) -> None:
        self.timeout = timeout
        self.theme_strategies = theme_strategies or {}

    def search(self, theme: str, count: int) -> list[Book]:
        books: list[Book] = []
        seen_keys: set[str] = set()

        for query in self._queries_for_theme(theme):
            try:
                response = requests.get(
                    "https://openlibrary.org/search.json",
                    params={
                        "q": query,
                        "language": "chi",
                        "limit": max(count * 3, count),
                        "fields": "title,author_name,isbn,cover_i,first_sentence,language",
                    },
                    timeout=(3, self.timeout),
                )
                response.raise_for_status()
            except requests.RequestException:
                continue

            candidates = []
            for item in response.json().get("docs") or []:
                book = self._book_from_doc(item)
                if not book:
                    continue
                quality = _chinese_quality_score(
                    book.title,
                    book.author,
                    book.summary,
                    item.get("language") or [],
                )
                if quality <= 0:
                    continue
                candidates.append((quality, book))

            for _, book in sorted(candidates, key=lambda item: item[0], reverse=True):
                key = book.isbn or "".join(book.title.split()).lower()
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                books.append(book)
                if len(books) >= count:
                    return books

        return books

    def find_cover(self, book: Book) -> str | None:
        if not book.isbn:
            return None

        response = requests.get(
            f"https://openlibrary.org/isbn/{book.isbn}.json",
            timeout=(3, self.timeout),
        )
        if response.status_code != 200:
            return None

        return f"https://covers.openlibrary.org/b/isbn/{book.isbn}-L.jpg"

    def _queries_for_theme(self, theme: str) -> list[str]:
        queries = [theme]
        strategy = self.theme_strategies.get(theme) or {}
        for value in (strategy.get("tags") or []) + (strategy.get("keywords") or []):
            query = str(value).replace("书单", "").strip()
            if query and query not in queries:
                queries.append(query)
        return queries

    def _book_from_doc(self, item: dict) -> Book | None:
        title = (item.get("title") or "").strip()
        if not title:
            return None

        authors = item.get("author_name") or []
        author = "、".join(author.strip() for author in authors if author and author.strip()) or "未知作者"
        isbn = self._extract_isbn(item.get("isbn") or [])
        cover = None
        if item.get("cover_i"):
            cover = f"https://covers.openlibrary.org/b/id/{item['cover_i']}-L.jpg"

        return Book(
            title=title,
            author=author,
            rating=None,
            cover=cover,
            summary=self._extract_summary(item),
            source=self.source_label,
            isbn=isbn,
        )

    def _extract_isbn(self, identifiers: list[str]) -> str | None:
        for identifier in identifiers:
            normalized = identifier.replace("-", "").strip().upper()
            if normalized:
                return normalized
        return None

    def _extract_summary(self, item: dict) -> str:
        first_sentence = item.get("first_sentence")
        if isinstance(first_sentence, list):
            for sentence in first_sentence:
                if sentence and str(sentence).strip():
                    return str(sentence).strip()
        if isinstance(first_sentence, str) and first_sentence.strip():
            return first_sentence.strip()
        return "暂无简介"


def _chinese_quality_score(title: str, author: str, summary: str, languages: list[str]) -> float:
    text = f"{title} {author} {summary}"
    ratio = _chinese_ratio(text)
    normalized_languages = {str(language).lower() for language in languages}
    language_bonus = 1.0 if normalized_languages & CHINESE_LANGUAGE_CODES else 0.0
    if ratio < MIN_CHINESE_RATIO and not language_bonus:
        return 0.0
    return ratio + language_bonus


def _chinese_ratio(text: str) -> float:
    meaningful_chars = [char for char in text if not char.isspace()]
    if not meaningful_chars:
        return 0.0
    chinese_chars = [char for char in meaningful_chars if "\u4e00" <= char <= "\u9fff"]
    return len(chinese_chars) / len(meaningful_chars)