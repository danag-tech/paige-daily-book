from abc import ABC, abstractmethod

from models import Book


class UnsupportedProviderError(Exception):
    """Raised when a provider cannot support theme-based recommendations."""


class BookProvider(ABC):
    name: str
    source_label: str

    @abstractmethod
    def search(self, theme: str, count: int) -> list[Book]:
        """Recommend books by theme and return normalized Book objects."""

    def find_cover(self, book: Book) -> str | None:
        """Find a replacement cover URL for an existing book."""
        return None
