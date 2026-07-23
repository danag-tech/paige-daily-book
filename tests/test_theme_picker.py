import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import theme_picker


class ThemePickerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.history_path = Path(self.temp_dir.name) / "data" / "theme_history.json"
        self.themes = ["音乐", "创业", "商业", "管理", "经济"]
        self.today = date(2026, 7, 23)
        self.path_patch = patch.object(theme_picker, "THEME_HISTORY_PATH", self.history_path)
        self.themes_patch = patch.object(theme_picker, "THEMES", self.themes)
        self.path_patch.start()
        self.themes_patch.start()

    def tearDown(self):
        self.themes_patch.stop()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def write_history(self, records):
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    def test_random_theme_is_selected(self):
        with patch("theme_picker.random.choice", return_value="管理") as choice:
            selected = theme_picker.get_today_theme(self.today)
        self.assertEqual(selected, "管理")
        choice.assert_called_once()

    def test_recent_three_days_are_excluded(self):
        self.write_history([
            {"date": "2026-07-21", "theme": "音乐"},
            {"date": "2026-07-22", "theme": "创业"},
            {"date": "2026-07-23", "theme": "商业"},
        ])
        with patch("theme_picker.random.choice", side_effect=lambda candidates: candidates[0]):
            selected = theme_picker.get_today_theme(self.today)
        self.assertNotIn(selected, {"音乐", "创业", "商业"})

    def test_all_recent_themes_relax_the_restriction(self):
        self.write_history([
            {"date": (self.today - timedelta(days=2)).isoformat(), "theme": theme}
            for theme in self.themes
        ])
        with patch("theme_picker.random.choice", return_value="音乐") as choice:
            selected = theme_picker.get_today_theme(self.today)
        self.assertEqual(selected, "音乐")
        self.assertEqual(choice.call_args.args[0], self.themes)

    def test_missing_history_file_is_created(self):
        self.assertFalse(self.history_path.exists())
        with patch("theme_picker.random.choice", return_value="音乐"):
            selected = theme_picker.get_today_theme(self.today)
        self.assertEqual(selected, "音乐")
        self.assertTrue(self.history_path.exists())
        self.assertEqual(json.loads(self.history_path.read_text(encoding="utf-8")), [])

    def test_save_history_keeps_latest_thirty_records(self):
        self.write_history([
            {"date": (self.today - timedelta(days=offset)).isoformat(), "theme": "音乐"}
            for offset in range(30, 0, -1)
        ])
        theme_picker.save_theme_history("创业", self.today)
        history = json.loads(self.history_path.read_text(encoding="utf-8"))
        self.assertEqual(len(history), 30)
        self.assertEqual(history[-1], {"date": "2026-07-23", "theme": "创业"})

    def test_ordered_themes_keeps_fallback_behavior(self):
        self.write_history([{ "date": "2026-07-23", "theme": "音乐" }])
        with patch("theme_picker.random.choice", return_value="创业"):
            ordered = theme_picker.get_ordered_themes()
        self.assertEqual(ordered[0], "创业")
        self.assertEqual(set(ordered), set(self.themes))
        self.assertEqual(len(ordered), len(self.themes))


if __name__ == "__main__":
    unittest.main()
