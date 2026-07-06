import json
import sys
from pathlib import Path

from config import ConfigError, get_deepseek_config
from email_sender import send_email
from prompt_builder import build_summary_prompt
from providers.manager import ProviderManager
from summary_generator import SummaryGenerationError, generate_summary
from theme_picker import get_today_theme


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_books(theme: str) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"Today theme: {theme}")

    try:
        deepseek_config = get_deepseek_config()
        app_config = load_config()
        manager = ProviderManager(app_config)
        result = manager.search(theme, app_config["book_count"])
        prompt = build_summary_prompt(result.books)
        summary = generate_summary(prompt, deepseek_config)
        print(summary)
        send_email(f"今日荐书：{theme}", summary)
    except ConfigError as exc:
        print(f"配置错误：{exc}")
        return
    except SummaryGenerationError as exc:
        print(f"总结生成失败：{exc}")
        return
    except Exception as exc:
        print(f"程序运行失败：{exc}")
        return

    print("Email sent successfully.")


if __name__ == "__main__":
    theme = get_today_theme()
    print_books(theme)
