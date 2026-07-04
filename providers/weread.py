from models import Book
from providers.base import BookProvider, UnsupportedProviderError


class WeReadProvider(BookProvider):
    name = "weread"
    source_label = "微信读书"

    def __init__(self, timeout: int = 8) -> None:
        self.timeout = timeout

    def search(self, theme: str, count: int) -> list[Book]:
        raise UnsupportedProviderError("微信读书当前实现只有关键词搜索，不支持主题书籍推荐")
