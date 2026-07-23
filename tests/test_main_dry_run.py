import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main


class MainDryRunTests(unittest.TestCase):
    preview_path = Path(__file__).resolve().parents[1] / "archive" / "dry-run-email-preview.html"

    def tearDown(self):
        if self.preview_path.exists():
            self.preview_path.unlink()

    def test_dry_run_generates_preview_and_skips_side_effects(self):
        books = [
            SimpleNamespace(title=f"测试书{i}", author="测试作者", rating="8.0", summary="原简介", isbn=None, cover=None)
            for i in range(1, 4)
        ]
        generated = SimpleNamespace(
            book_summaries=[f"生成简介{i}" for i in range(1, 4)],
            daily_text="今日测试荐书",
        )
        app_config = {"book_count": 3}
        manager = SimpleNamespace(search=lambda theme, count: SimpleNamespace(books=[]))

        with patch.object(main, "get_deepseek_config", return_value=object()), \
             patch.object(main, "load_config", return_value=app_config), \
             patch.object(main, "ProviderManager", return_value=manager), \
             patch.object(main, "load_sent_books", return_value=[]), \
             patch.object(main, "load_book_pool", return_value=[]), \
             patch.object(main, "get_ordered_themes", return_value=["测试主题"]), \
             patch.object(main, "get_pool_books", return_value=books), \
             patch.object(main, "filter_quality_books", side_effect=lambda items, source: items), \
             patch.object(main, "filter_unsent_books", side_effect=lambda items, sent: items), \
             patch.object(main, "generate_summary_result", return_value=generated), \
             patch.object(main, "download_cover_images", return_value=[None, None, None]), \
             patch.object(main, "send_email") as send_email, \
             patch.object(main, "append_sent_books") as append_sent_books, \
             patch.object(main, "save_sent_books") as save_sent_books, \
             patch.object(main, "refresh_book_pool") as refresh_book_pool, \
             patch.object(main, "save_book_pool") as save_book_pool, \
             patch.object(main, "_update_website_data_safely") as update_website:
            main.print_books(dry_run=True)

        self.assertTrue(self.preview_path.exists())
        preview = self.preview_path.read_text(encoding="utf-8")
        self.assertEqual(preview.count("<h3 "), 3)
        self.assertIn("生成简介1", preview)
        send_email.assert_not_called()
        append_sent_books.assert_not_called()
        save_sent_books.assert_not_called()
        refresh_book_pool.assert_not_called()
        save_book_pool.assert_not_called()
        update_website.assert_not_called()


if __name__ == "__main__":
    unittest.main()
