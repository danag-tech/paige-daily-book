import requests

from models import Book
from providers.base import BookProvider, UnsupportedProviderError


class OpenLibraryProvider(BookProvider):
    name = "openlibrary"
    source_label = "Open Library"

    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout

    def search(self, theme: str, count: int) -> list[Book]:
        raise UnsupportedProviderError("Open Library 当前实现只有关键词搜索，不支持主题书籍推荐")

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
