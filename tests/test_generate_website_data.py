import unittest

from generate_website_data import generate_website_books


class WebsiteHistoryTests(unittest.TestCase):
    @staticmethod
    def record(sent_date=None, title="鞋狗", author="菲尔·奈特"):
        record = {
            "title": title,
            "author": author,
            "rating": "8.5",
            "cover": "https://example.com/cover.jpg",
            "summary": "一本关于创业与坚持的书。",
        }
        if sent_date is not None:
            record["sent_date"] = sent_date
        return record

    def test_same_book_on_different_dates_is_preserved(self):
        books = generate_website_books([
            self.record("2026-07-01"),
            self.record("2026-10-01"),
        ])
        self.assertEqual(len(books), 2)
        self.assertEqual(
            [book["recommended_date"] for book in books],
            ["2026-10-01", "2026-07-01"],
        )

    def test_same_book_on_same_date_is_deduplicated(self):
        books = generate_website_books([
            self.record("2026-07-01"),
            self.record("2026-07-01"),
        ])
        self.assertEqual(len(books), 1)

    def test_history_is_sorted_newest_first(self):
        books = generate_website_books([
            self.record("2026-06-01", "书一"),
            self.record("2026-08-01", "书二"),
            self.record("2026-07-01", "书三"),
        ])
        self.assertEqual(
            [book["recommended_date"] for book in books],
            ["2026-08-01", "2026-07-01", "2026-06-01"],
        )

    def test_legacy_record_without_sent_date_still_generates(self):
        books = generate_website_books([self.record()])
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]["recommended_date"], "暂无日期")


if __name__ == "__main__":
    unittest.main()
