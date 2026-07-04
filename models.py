from dataclasses import dataclass


@dataclass
class Book:
    title: str
    author: str
    rating: str | None
    cover: str | None
    summary: str
    source: str
    isbn: str | None = None
