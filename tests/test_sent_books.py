import unittest
from datetime import date, timedelta
from types import SimpleNamespace

from sent_books import append_sent_books, filter_unsent_books, get_cooldown_keys


class SentBooksCooldownTests(unittest.TestCase):
    def setUp(self):
        self.book = SimpleNamespace(
            title="测试书",
            author="测试作者",
            isbn="9780000000001",
            rating="8.0",
            cover=None,
            summary="测试简介",
            source="test",
        )
        self.today = date.today()

    def record(self, sent_date):
        return {
            "title": self.book.title,
            "author": self.book.author,
            "isbn": self.book.isbn,
            "sent_date": sent_date,
        }

    def test_ten_days_ago_is_excluded(self):
        records = [self.record((self.today - timedelta(days=10)).isoformat())]
        self.assertEqual(filter_unsent_books([self.book], records), [])

    def test_ninety_day_boundary_is_excluded(self):
        records = [self.record((self.today - timedelta(days=90)).isoformat())]
        self.assertEqual(filter_unsent_books([self.book], records), [])

    def test_ninety_one_days_ago_is_allowed(self):
        records = [self.record((self.today - timedelta(days=91)).isoformat())]
        self.assertEqual(filter_unsent_books([self.book], records), [self.book])

    def test_missing_or_invalid_date_is_excluded(self):
        for sent_date in (None, "", "not-a-date"):
            with self.subTest(sent_date=sent_date):
                self.assertEqual(filter_unsent_books([self.book], [self.record(sent_date)]), [])

    def test_append_uses_the_same_cooldown_rule(self):
        recent = [self.record((self.today - timedelta(days=10)).isoformat())]
        expired = [self.record((self.today - timedelta(days=91)).isoformat())]
        self.assertEqual(len(append_sent_books(recent, [self.book], "测试主题")), 1)
        self.assertEqual(len(append_sent_books(expired, [self.book], "测试主题")), 2)

    def test_cooldown_keys_include_invalid_date_records(self):
        self.assertTrue(get_cooldown_keys([self.record("invalid")]))


if __name__ == "__main__":
    unittest.main()
