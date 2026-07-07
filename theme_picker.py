import json
from datetime import date
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("config.json")


def _load_configured_themes() -> list[str]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    themes = list(config.get("theme_strategies", {}).keys())
    if not themes:
        raise RuntimeError("未配置任何可用主题发现策略")
    return themes


THEMES = _load_configured_themes()


def get_today_theme() -> str:
    today = date.today()
    index = today.toordinal() % len(THEMES)
    return THEMES[index]
