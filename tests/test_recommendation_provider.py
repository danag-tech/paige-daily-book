import unittest
from unittest.mock import patch

import requests

from models import Book
from providers.manager import ProviderManager
from providers.recommendation import RecommendationProvider


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class FakeSession:
    def __init__(self, responses=None, error=None):
        self.calls = []
        self.responses = list(responses or [])
        self.error = error

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error and "tag/" in url:
            raise self.error
        return self.responses.pop(0)


TAG_HTML = """
<div class="subject-item">
  <h2><a href="https://book.douban.com/subject/1/">测试书</a></h2>
  <div class="rating_nums">8.5</div>
  <span class="pl">100人评价</span>
  <div class="pub">测试作者 / 出版社 / 2024</div>
  <div class="pic"><img src="https://img.example/cover.jpg"></div>
  <div class="info"><p>测试简介</p></div>
</div>
"""

DETAIL_HTML = """
<div id="info">ISBN: 978-7-000-00000-1</div>
<div id="mainpic"><img src="https://img.example/detail.jpg"></div>
<span class="rating_num">8.6</span>
<div class="rating_people"><span>200人评价</span></div>
<div id="link-report"><span class="all"><div class="intro"><p>详情简介</p></div></span></div>
"""


class RecommendationProviderTests(unittest.TestCase):
    def test_session_is_warmed_and_headers_are_kept(self):
        session = FakeSession([
            FakeResponse(),
            FakeResponse(TAG_HTML),
            FakeResponse(DETAIL_HTML),
        ])
        with patch("providers.recommendation.requests.Session", return_value=session):
            provider = RecommendationProvider(
                pages_per_tag=1,
                theme_strategies={"测试主题": {"tags": ["测试"]}},
            )
            books = provider.search("测试主题", 1)

        self.assertEqual(len(books), 1)
        self.assertIsInstance(books[0], Book)
        self.assertEqual(books[0].title, "测试书")
        self.assertEqual(books[0].isbn, "9787000000001")
        self.assertEqual(session.calls[0][0], "https://book.douban.com/")
        for _, kwargs in session.calls:
            headers = kwargs["headers"]
            self.assertTrue(headers["User-Agent"])
            self.assertEqual(headers["Referer"], "https://book.douban.com/")
            self.assertIn("Accept-Language", headers)

    def test_tag_requests_wait_between_requests(self):
        session = FakeSession([
            FakeResponse(),
            FakeResponse(),
            FakeResponse(),
        ])
        with patch("providers.recommendation.requests.Session", return_value=session), \
             patch("providers.recommendation.random.uniform", return_value=2.0) as uniform, \
             patch("providers.recommendation.time.sleep") as sleep:
            provider = RecommendationProvider(
                pages_per_tag=1,
                theme_strategies={"测试主题": {"tags": ["测试"]}},
            )
            provider._collect_tag_candidates(["主题一", "主题二"])

        uniform.assert_called_once_with(1, 3)
        sleep.assert_called_once_with(2.0)

    def test_request_failure_reaches_existing_manager_fallback(self):
        session = FakeSession([FakeResponse()], error=requests.HTTPError("403"))
        fallback_book = Book(
            title="Fallback书",
            author="Fallback作者",
            rating="⭐8.0",
            cover=None,
            summary="Fallback简介",
            source="fallback",
            isbn=None,
        )
        fallback = type("FallbackProvider", (), {
            "name": "openlibrary",
            "source_label": "OpenLibrary",
            "search": lambda self, theme, count: [fallback_book],
            "find_cover": lambda self, book: None,
        })()
        with patch("providers.recommendation.requests.Session", return_value=session):
            recommendation = RecommendationProvider(pages_per_tag=1)

        manager = ProviderManager.__new__(ProviderManager)
        manager.config = {"theme_source": "test"}
        manager.providers = [recommendation, fallback]
        result = manager.search("测试主题", 1)
        self.assertEqual([book.title for book in result.books], ["Fallback书"])
        self.assertTrue(any("recommendation" in failure for failure in result.failures))


if __name__ == "__main__":
    unittest.main()
