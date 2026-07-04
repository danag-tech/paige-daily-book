import re
from dataclasses import dataclass
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from models import Book
from providers.base import BookProvider, UnsupportedProviderError


@dataclass
class CandidateBook:
    title: str
    author: str
    rating: float
    rating_count: int
    cover: str | None
    summary: str
    detail_url: str
    occurrence_count: int = 1
    isbn: str | None = None


class RecommendationProvider(BookProvider):
    name = "recommendation"
    source_label = "豆瓣读书标签页"

    def __init__(
        self,
        timeout: int = 8,
        min_rating: float = 7.5,
        summary_max_length: int = 800,
        theme_strategies: dict[str, dict] | None = None,
        pages_per_tag: int = 2,
    ) -> None:
        self.timeout = timeout
        self.min_rating = min_rating
        self.summary_max_length = summary_max_length
        self.theme_strategies = theme_strategies or {}
        self.pages_per_tag = pages_per_tag

    def search(self, theme: str, count: int) -> list[Book]:
        strategy = self.theme_strategies.get(theme)
        if not strategy:
            raise UnsupportedProviderError(f"未配置主题「{theme}」的发现策略")

        tags = self._strategy_tags(strategy)
        if not tags:
            raise UnsupportedProviderError(f"主题「{theme}」没有可用 tags，无法发现候选书")

        candidates = self._collect_tag_candidates(tags)
        ranked_candidates = self._rank_candidates(candidates)

        books: list[Book] = []
        seen_isbn_or_titles: set[str] = set()

        for candidate in ranked_candidates:
            enriched = self._enrich_candidate(candidate)
            dedupe_key = enriched.isbn or self._normalize_title(enriched.title)
            if dedupe_key in seen_isbn_or_titles:
                continue

            seen_isbn_or_titles.add(dedupe_key)
            books.append(
                Book(
                    title=enriched.title,
                    author=enriched.author,
                    rating=f"⭐{enriched.rating:.1f}",
                    cover=enriched.cover,
                    summary=self._truncate(enriched.summary),
                    source=self.source_label,
                    isbn=enriched.isbn,
                )
            )

            if len(books) >= count:
                break

        return books

    def _strategy_tags(self, strategy: dict) -> list[str]:
        tags: list[str] = []
        for tag in strategy.get("tags") or []:
            if tag and tag not in tags:
                tags.append(tag)

        for keyword in strategy.get("keywords") or []:
            tag = keyword.replace("书单", "").strip()
            if tag and tag not in tags:
                tags.append(tag)

        return tags

    def _collect_tag_candidates(self, tags: list[str]) -> dict[str, CandidateBook]:
        candidates: dict[str, CandidateBook] = {}

        for tag in tags:
            for page in range(self.pages_per_tag):
                url = f"https://book.douban.com/tag/{quote(tag)}?start={page * 20}&type=T"
                response = requests.get(url, headers=self._headers(), timeout=(3, self.timeout))
                if response.status_code == 404:
                    break
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                for item in soup.select(".subject-item"):
                    candidate = self._parse_tag_item(item)
                    if not candidate or candidate.rating < self.min_rating:
                        continue

                    key = self._normalize_title(candidate.title)
                    existing = candidates.get(key)
                    if existing:
                        existing.occurrence_count += 1
                        existing.rating_count = max(existing.rating_count, candidate.rating_count)
                        existing.rating = max(existing.rating, candidate.rating)
                    else:
                        candidates[key] = candidate

        return candidates

    def _parse_tag_item(self, item: BeautifulSoup) -> CandidateBook | None:
        title_node = item.select_one("h2 a")
        if not title_node:
            return None

        title = " ".join(title_node.get_text(" ", strip=True).split())
        detail_url = title_node.get("href")
        rating = self._rating_value(self._first_text(item, [".rating_nums"]))
        rating_count = self._rating_count(self._first_text(item, [".pl"]))
        if not title or not detail_url or rating is None:
            return None

        info = self._first_text(item, [".pub"]) or ""
        cover_node = item.select_one(".pic img")
        summary = self._first_text(item, [".info p"]) or "暂无简介"

        return CandidateBook(
            title=title,
            author=self._extract_author(info),
            rating=rating,
            rating_count=rating_count,
            cover=cover_node.get("src") if cover_node else None,
            summary=summary,
            detail_url=detail_url,
        )

    def _rank_candidates(self, candidates: dict[str, CandidateBook]) -> list[CandidateBook]:
        return sorted(
            candidates.values(),
            key=lambda candidate: (
                candidate.occurrence_count,
                candidate.rating_count,
                candidate.rating,
            ),
            reverse=True,
        )

    def _enrich_candidate(self, candidate: CandidateBook) -> CandidateBook:
        response = requests.get(candidate.detail_url, headers=self._headers(), timeout=(3, self.timeout))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        isbn = self._isbn_from_detail(soup)
        detail_summary = self._summary_from_detail(soup)
        cover_node = soup.select_one("#mainpic img")
        rating = self._rating_value(self._first_text(soup, [".rating_num"]))
        rating_count = self._rating_count(self._first_text(soup, [".rating_people span", ".rating_people"]))

        candidate.isbn = isbn
        candidate.summary = detail_summary or candidate.summary
        candidate.cover = cover_node.get("src") if cover_node else candidate.cover
        candidate.rating = rating if rating is not None else candidate.rating
        candidate.rating_count = rating_count or candidate.rating_count
        return candidate

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://book.douban.com/",
        }

    def _first_text(self, soup: BeautifulSoup, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                text = " ".join(node.get_text(" ", strip=True).split())
                if text:
                    return text
        return None

    def _summary_from_detail(self, soup: BeautifulSoup) -> str | None:
        nodes = soup.select("#link-report span.all .intro p")
        if not nodes:
            nodes = soup.select("#link-report .intro p")
        if not nodes:
            nodes = soup.select("#link-report .intro")

        paragraphs: list[str] = []
        seen: set[str] = set()
        for node in nodes:
            paragraph = " ".join(node.get_text(" ", strip=True).split())
            paragraph = paragraph.replace("(展开全部)", "").strip()
            if not paragraph or paragraph in seen:
                continue
            seen.add(paragraph)
            paragraphs.append(paragraph)

        return "\n".join(paragraphs) or None

    def _isbn_from_detail(self, soup: BeautifulSoup) -> str | None:
        info = self._first_text(soup, ["#info"]) or ""
        match = re.search(r"ISBN:\s*([0-9Xx-]+)", info)
        if not match:
            return None
        return match.group(1).replace("-", "").upper()

    def _rating_value(self, rating: str | None) -> float | None:
        if not rating:
            return None
        try:
            return float(rating.replace("⭐", "").strip())
        except ValueError:
            return None

    def _rating_count(self, text: str | None) -> int:
        if not text:
            return 0
        match = re.search(r"([0-9,]+)\s*人评价", text)
        if not match:
            match = re.search(r"([0-9,]+)", text)
        if not match:
            return 0
        return int(match.group(1).replace(",", ""))

    def _extract_author(self, info: str) -> str:
        if not info:
            return "未知作者"
        return info.split("/")[0].strip() or "未知作者"

    def _truncate(self, summary: str) -> str:
        if len(summary) > self.summary_max_length:
            return summary[: self.summary_max_length].rstrip() + "..."
        return summary

    def _normalize_title(self, title: str) -> str:
        return "".join(title.split()).replace("《", "").replace("》", "").lower()
