import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import main
from book_pool import refresh_book_pool
from models import Book


class PoolReplenishmentTests(unittest.TestCase):
    def records(self, count, theme):
        return [
            {"theme": theme, "title": f"{theme}-{i}", "author": "作者", "isbn": None}
            for i in range(count)
        ]

    def book(self, title, author="作者"):
        return Book(
            title=title,
            author=author,
            rating="⭐8.0",
            cover="https://example.com/cover.jpg",
            summary="简介",
            source="provider",
            isbn=None,
        )

    def test_pool_150_does_not_trigger_replenishment(self):
        manager = Mock()
        records = self.records(150, "音乐")
        result = main._replenish_book_pool(records, manager, [], 9, ["音乐", "创业"])
        self.assertIs(result, records)
        manager.search.assert_not_called()

    def test_pool_50_triggers_replenishment(self):
        manager = Mock()
        manager.search.return_value = SimpleNamespace(books=[])
        records = self.records(50, "音乐")
        main._replenish_book_pool(records, manager, [], 9, ["音乐", "创业"])
        self.assertTrue(manager.search.called)

    def test_understocked_themes_are_prioritized(self):
        calls = []
        manager = Mock()

        def search(theme, count):
            calls.append(theme)
            return SimpleNamespace(books=[])

        manager.search.side_effect = search
        records = self.records(10, "音乐") + self.records(8, "创业") + self.records(1, "历史")
        main._replenish_book_pool(records, manager, [], 9, ["音乐", "创业", "AI", "历史"])
        self.assertEqual(calls[:2], ["AI", "历史"])

    def test_fifty_provider_candidates_are_limited_to_twenty(self):
        manager = Mock()
        manager.search.return_value = SimpleNamespace(
            books=[self.book(f"candidate-{i}") for i in range(50)]
        )
        records = self.records(30, "音乐") + self.records(20, "创业")
        result = main._replenish_book_pool(records, manager, [], 9, ["音乐", "创业", "AI"])
        self.assertEqual(len(result) - len(records), 20)

    def test_five_provider_candidates_are_all_added(self):
        manager = Mock()
        manager.search.return_value = SimpleNamespace(
            books=[self.book(f"candidate-{i}") for i in range(5)]
        )
        records = self.records(30, "音乐") + self.records(20, "创业")
        result = main._replenish_book_pool(records, manager, [], 9, ["音乐", "创业", "AI"])
        self.assertEqual(len(result) - len(records), 5)
    def test_single_theme_is_capped_at_thirty(self):
        discovered = [self.book(f"候选书-{i}") for i in range(31)]
        refreshed = refresh_book_pool([], "音乐", discovered, [], [])
        self.assertEqual(len(refreshed), 30)

    def test_provider_failure_does_not_raise_or_change_pool(self):
        manager = Mock()
        manager.search.side_effect = RuntimeError("provider unavailable")
        records = self.records(50, "音乐")
        result = main._replenish_book_pool(records, manager, [], 9, ["音乐", "创业"])
        self.assertEqual(result, records)

    def test_replenishment_does_not_append_sent_records(self):
        manager = Mock()
        manager.search.return_value = SimpleNamespace(books=[self.book("补充书")])
        sent_records = []
        records = self.records(50, "音乐")
        result = main._replenish_book_pool(records, manager, sent_records, 9, ["音乐", "创业"])
        self.assertEqual(sent_records, [])
        self.assertTrue(any(record.get("title") == "补充书" for record in result))


if __name__ == "__main__":
    unittest.main()
