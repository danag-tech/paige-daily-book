import requests

from models import Book
from providers.base import BookProvider, UnsupportedProviderError


class GoogleBooksProvider(BookProvider):
    name = "googlebooks"
    source_label = "Google Books"

    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout

    def search(self, theme: str, count: int) -> list[Book]:
        raise UnsupportedProviderError("Google Books 当前实现只有关键词搜索，不支持主题书籍推荐")

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
