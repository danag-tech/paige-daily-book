import re
import unittest
from types import SimpleNamespace

from html_email_builder import _build_book_links, _build_book_links_html, build_book_email_html


class HtmlEmailBuilderTests(unittest.TestCase):
    def test_isbn_builds_three_links(self):
        book = {"title": "百年孤独", "author": "加西亚·马尔克斯", "isbn": "978-7-02-016473-7"}
        links = _build_book_links(book)
        self.assertEqual(links["douban"], "https://book.douban.com/isbn/9787020164737/")
        self.assertIn("https://weread.qq.com/web/search/books?keyword=", links["weread"])
        self.assertIn("keyword=9787020164737", links["jd"])
        html = _build_book_links_html(book)
        self.assertEqual(html.count("<a "), 3)

    def test_missing_isbn_hides_douban_but_keeps_searches(self):
        book = {"title": "百年孤独", "author": "加西亚·马尔克斯"}
        links = _build_book_links(book)
        self.assertNotIn("douban", links)
        html = _build_book_links_html(book)
        self.assertNotIn("豆瓣详情", html)
        self.assertIn("微信读书", html)
        self.assertIn("京东购买", html)

    def test_special_characters_are_escaped_and_encoded(self):
        book = SimpleNamespace(
            title="《苏菲的世界》",
            author="[挪威]乔斯坦·贾德",
            rating="8.5",
            summary='<script>alert("x")</script>',
            isbn=None,
            cover=None,
        )
        html = build_book_email_html("哲学", [book], "", [None])
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("%E8%8B%8F%E8%8F%B2", html)
        self.assertIn("%5B%E6%8C%AA%E5%A8%81%5D", html)

    def test_no_empty_or_none_href(self):
        html = _build_book_links_html({"title": "测试", "author": "作者", "isbn": None})
        self.assertNotIn('href=""', html)
        self.assertNotIn('href="None"', html)
        for href in re.findall(r'href="([^"]*)"', html):
            self.assertTrue(href.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
