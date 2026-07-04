from collections.abc import Iterable
from dataclasses import dataclass

import requests

from models import Book
from providers.base import BookProvider
from providers.douban import DoubanProvider
from providers.googlebooks import GoogleBooksProvider
from providers.openlibrary import OpenLibraryProvider
from providers.recommendation import RecommendationProvider
from providers.weread import WeReadProvider


@dataclass
class SearchResult:
    books: list[Book]
    theme_source: str
    book_info_source: str
    failures: list[str]


class ProviderManager:
    provider_registry = {
        "recommendation": RecommendationProvider,
        "douban": DoubanProvider,
        "weread": WeReadProvider,
        "openlibrary": OpenLibraryProvider,
        "googlebooks": GoogleBooksProvider,
    }

    def __init__(self, config: dict) -> None:
        self.config = config
        self.cover_timeout = config.get("cover_check_timeout", 3)
        self.providers = self._build_providers(config.get("provider_order", []))

    def search(self, theme: str, count: int) -> SearchResult:
        failures: list[str] = []

        for provider_index, provider in enumerate(self.providers):
            try:
                books = provider.search(theme, count)
            except Exception as exc:
                failures.append(f"{provider.name}: {exc}")
                continue

            unique_books = self._dedupe(books)
            if len(unique_books) >= count:
                selected_books = unique_books[:count]
                self._ensure_covers(selected_books, provider_index, failures)
                return SearchResult(
                    books=selected_books,
                    theme_source=self.config.get("theme_source", "config.json 主题发现策略"),
                    book_info_source=provider.source_label,
                    failures=failures,
                )

            failures.append(f"{provider.name}: 主题推荐结果不足，仅返回 {len(unique_books)} 本")

        if failures:
            error_message = "没有 Provider 成功返回足够的主题推荐书籍。 " + " | ".join(failures)
            raise RuntimeError(error_message)

        raise RuntimeError("未配置 Provider。")

    def _build_providers(self, provider_order: Iterable[str]) -> list[BookProvider]:
        providers: list[BookProvider] = []
        for provider_name in provider_order:
            provider_class = self.provider_registry.get(provider_name)
            if not provider_class:
                continue

            if provider_name == "recommendation":
                providers.append(
                    provider_class(
                        min_rating=self.config.get("min_rating", 7.5),
                        summary_max_length=self.config.get("summary_max_length", 800),
                        theme_strategies=self.config.get("theme_strategies", {}),
                        pages_per_tag=self.config.get("pages_per_tag", 2),
                    )
                )
            else:
                providers.append(provider_class())
        return providers

    def _dedupe(self, books: list[Book]) -> list[Book]:
        unique_books: list[Book] = []
        seen_keys: set[str] = set()

        for book in books:
            dedupe_key = book.isbn or "".join(book.title.split()).replace("《", "").replace("》", "").lower()
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            unique_books.append(book)

        return unique_books

    def _ensure_covers(
        self,
        books: list[Book],
        successful_provider_index: int,
        failures: list[str],
    ) -> None:
        fallback_providers = self.providers[successful_provider_index + 1 :]

        for book in books:
            if book.cover and self._cover_is_available(book.cover):
                continue

            if book.cover:
                failures.append(f"cover: {book.title} 的封面 URL 不可用，尝试后续 Provider")

            replacement_cover = self._find_replacement_cover(book, fallback_providers, failures)
            if replacement_cover:
                book.cover = replacement_cover

    def _cover_is_available(self, url: str) -> bool:
        try:
            response = requests.head(
                url,
                headers=self._headers(),
                timeout=(2, self.cover_timeout),
                allow_redirects=True,
            )
            return response.status_code < 400
        except requests.RequestException:
            return False

    def _find_replacement_cover(
        self,
        book: Book,
        fallback_providers: list[BookProvider],
        failures: list[str],
    ) -> str | None:
        for provider in fallback_providers:
            try:
                cover = provider.find_cover(book)
            except Exception as exc:
                failures.append(f"{provider.name}: 获取《{book.title}》替代封面失败：{exc}")
                continue

            if cover and self._cover_is_available(cover):
                return cover

        return None

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Referer": "https://book.douban.com/",
        }
