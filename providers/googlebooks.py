import requests

from models import Book
from providers.base import BookProvider


MIN_CHINESE_RATIO = 0.08


class GoogleBooksProvider(BookProvider):
    name = "googlebooks"
    source_label = "Google Books"

    def __init__(self, timeout: int = 8, theme_strategies: dict[str, dict] | None = None) -> None:
        self.timeout = timeout
        self.theme_strategies = theme_strategies or {}

    def search(self, theme: str, count: int) -> list[Book]:
        books: list[Book] = []
        seen_keys: set[str] = set()

        for query in self._queries_for_theme(theme):
            try:
                response = requests.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params={
                        "q": f"{query} 中文 书",
                        "maxResults": min(max(count * 2, count), 40),
                        "printType": "books",
                        "orderBy": "relevance",
                        "langRestrict": "zh",
                    },
                    timeout=(3, self.timeout),
                )
                response.raise_for_status()
            except requests.RequestException:
                continue

            candidates = []
            for item in response.json().get("items") or []:
                volume_info = item.get("volumeInfo") or {}
                book = self._book_from_volume_info(volume_info)
                if not book:
                    continue
                quality = _chinese_quality_score(
                    book.title,
                    book.author,
                    book.summary,
                    volume_info.get("language"),
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
        query = f"isbn:{book.isbn}" if book.isbn else f'intitle:"{book.title}"'
        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={
                "q": query,
                "maxResults": 1,
                "printType": "books",
            },
            timeout=(3, self.timeout),
        )
        if response.status_code != 200:
            return None

        items = response.json().get("items") or []
        if not items:
            return None

        image_links = items[0].get("volumeInfo", {}).get("imageLinks") or {}
        return image_links.get("thumbnail") or image_links.get("smallThumbnail")

    def _queries_for_theme(self, theme: str) -> list[str]:
        queries = [theme]
        strategy = self.theme_strategies.get(theme) or {}
        for value in (strategy.get("tags") or []) + (strategy.get("keywords") or []):
            query = str(value).replace("书单", "").strip()
            if query and query not in queries:
                queries.append(query)
        return queries

    def _book_from_volume_info(self, volume_info: dict) -> Book | None:
        title = (volume_info.get("title") or "").strip()
        if not title:
            return None

        authors = volume_info.get("authors") or []
        author = "、".join(author.strip() for author in authors if author and author.strip()) or "未知作者"
        isbn = self._extract_isbn(volume_info.get("industryIdentifiers") or [])
        image_links = volume_info.get("imageLinks") or {}
        rating = volume_info.get("averageRating")
        description = (volume_info.get("description") or "暂无简介").strip() or "暂无简介"

        return Book(
            title=title,
            author=author,
            rating=f"⭐{float(rating):.1f}" if isinstance(rating, (int, float)) else None,
            cover=image_links.get("thumbnail") or image_links.get("smallThumbnail"),
            summary=description,
            source=self.source_label,
            isbn=isbn,
        )

    def _extract_isbn(self, identifiers: list[dict]) -> str | None:
        for identifier_type in ("ISBN_13", "ISBN_10"):
            for identifier in identifiers:
                if identifier.get("type") == identifier_type and identifier.get("identifier"):
                    return identifier["identifier"].replace("-", "").upper()
        return None


def _chinese_quality_score(title: str, author: str, summary: str, language: str | None = None) -> float:
    text = f"{title} {author} {summary}"
    ratio = _chinese_ratio(text)
    language_bonus = 1.0 if str(language or "").lower() in {"zh", "zh-cn", "zh-tw", "chi", "zho"} else 0.0
    if ratio < MIN_CHINESE_RATIO and not language_bonus:
        return 0.0
    return ratio + language_bonus


def _chinese_ratio(text: str) -> float:
    meaningful_chars = [char for char in text if not char.isspace()]
    if not meaningful_chars:
        return 0.0
    chinese_chars = [char for char in meaningful_chars if "\u4e00" <= char <= "\u9fff"]
    return len(chinese_chars) / len(meaningful_chars)