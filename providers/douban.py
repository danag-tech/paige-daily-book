from models import Book
from providers.base import BookProvider, UnsupportedProviderError


class DoubanProvider(BookProvider):
    name = "douban"
    source_label = "豆瓣读书"

    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout

    def search(self, theme: str, count: int) -> list[Book]:
        raise UnsupportedProviderError("DoubanProvider 不再使用固定书单；请使用 RecommendationProvider 做主题发现")
