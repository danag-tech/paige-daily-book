import json
import random
from datetime import date, timedelta
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("config.json")
THEME_HISTORY_PATH = Path(__file__).with_name("data") / "theme_history.json"
THEME_HISTORY_LIMIT = 30
RECENT_THEME_DAYS = 3


def _load_configured_themes() -> list[str]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    themes = list(config.get("theme_strategies", {}).keys())
    if not themes:
        raise RuntimeError("未配置任何可用主题发现策略")
    return themes


def _load_theme_history() -> list[dict]:
    if not THEME_HISTORY_PATH.exists():
        THEME_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        THEME_HISTORY_PATH.write_text("[]\n", encoding="utf-8")
        return []

    try:
        with THEME_HISTORY_PATH.open("r", encoding="utf-8") as file:
            history = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(history, list):
        return []
    return [
        record
        for record in history
        if isinstance(record, dict)
        and isinstance(record.get("date"), str)
        and isinstance(record.get("theme"), str)
        and record.get("theme")
    ]


def get_recent_theme_history(today: date | None = None) -> list[dict]:
    reference_date = today or date.today()
    cutoff_date = reference_date - timedelta(days=RECENT_THEME_DAYS - 1)
    recent_history = []

    for record in _load_theme_history():
        try:
            record_date = date.fromisoformat(record["date"])
        except (TypeError, ValueError):
            continue
        if cutoff_date <= record_date <= reference_date:
            recent_history.append(record)

    return recent_history


def get_today_theme(today: date | None = None) -> str:
    reference_date = today or date.today()
    recent_themes = {record["theme"] for record in get_recent_theme_history(reference_date)}
    available_themes = [theme for theme in THEMES if theme not in recent_themes]
    candidates = available_themes or THEMES
    return random.choice(candidates)


def get_ordered_themes() -> list[str]:
    """Return a random eligible theme first, followed by fallback themes."""
    recent_themes = {record["theme"] for record in get_recent_theme_history()}
    available_themes = [theme for theme in THEMES if theme not in recent_themes]
    candidates = available_themes or list(THEMES)
    first_theme = random.choice(candidates)
    remaining_themes = [theme for theme in candidates if theme != first_theme]

    if available_themes:
        remaining_themes.extend(theme for theme in THEMES if theme in recent_themes)

    return [first_theme] + remaining_themes


def save_theme_history(theme: str, today: date | None = None) -> None:
    reference_date = today or date.today()
    history = _load_theme_history()
    history = [
        record
        for record in history
        if record.get("date") != reference_date.isoformat()
    ]
    history.append({"date": reference_date.isoformat(), "theme": theme})
    history = history[-THEME_HISTORY_LIMIT:]

    THEME_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with THEME_HISTORY_PATH.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
        file.write("\n")


THEMES = _load_configured_themes()
