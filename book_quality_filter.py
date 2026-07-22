from collections.abc import Iterable


REJECTED_TITLE_TERMS = (
    "词典",
    "辞典",
    "手册",
    "教材",
    "讲义",
    "教程",
    "习题",
    "大全",
    "全集",
    "论文集",
)

REJECTED_AUTHOR_TERMS = (
    "学院",
    "大学",
    "研究所",
    "教研组",
    "编写组",
)


def filter_quality_books(books: Iterable, source: str = "candidate") -> list:
    """Filter low-quality candidates and log every rejected book with reasons."""
    accepted_books = []
    for book in books:
        reasons = get_quality_rejection_reasons(book)
        if reasons:
            title = _display_value(getattr(book, "title", None), "untitled book")
            print(f"Quality filter rejected [{source}] {title}: {'; '.join(reasons)}")
            continue
        accepted_books.append(book)
    return accepted_books


def get_quality_rejection_reasons(book) -> list[str]:
    reasons = []
    title = _normalized_text(getattr(book, "title", None))
    author = _normalized_text(getattr(book, "author", None))

    matched_title_terms = [term for term in REJECTED_TITLE_TERMS if term in title]
    if matched_title_terms:
        reasons.append(f"title contains: {', '.join(matched_title_terms)}")

    matched_author_terms = [term for term in REJECTED_AUTHOR_TERMS if term in author]
    if matched_author_terms:
        reasons.append(f"author appears institutional: {', '.join(matched_author_terms)}")

    missing_fields = []

    if not _has_value(getattr(book, "cover", None)):
        missing_fields.append("cover")

    has_isbn = _has_value(getattr(book, "isbn", None))
    has_rating = _has_value(getattr(book, "rating", None))

    if not has_isbn and not has_rating:
        missing_fields.append("isbn_or_rating")

    if missing_fields:
        reasons.append(
            f"missing required quality fields: {', '.join(missing_fields)}"
        )

    return reasons


def _normalized_text(value) -> str:
    if value is None:
        return ""
    return "".join(str(value).split()).lower()


def _has_value(value) -> bool:
    return value is not None and bool(str(value).strip())


def _display_value(value, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback