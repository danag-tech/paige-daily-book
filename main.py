import json
import sys
from pathlib import Path

from config import ConfigError, get_deepseek_config
from cover_image import download_cover_images
from email_sender import send_email
from html_email_builder import build_book_email_html
from prompt_builder import build_summary_prompt
from providers.manager import ProviderManager
from sent_books import append_sent_books, filter_unsent_books, load_sent_books, save_sent_books
from summary_generator import SummaryGenerationError, generate_summary
from theme_picker import get_ordered_themes


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_books() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        deepseek_config = get_deepseek_config()
        app_config = load_config()
        book_count = app_config["book_count"]
        candidate_count = max(book_count * 3, 9)
        manager = ProviderManager(app_config)
        sent_records = load_sent_books()

        selected_theme = None
        selected_books = []
        for theme in get_ordered_themes():
            print(f"Trying theme: {theme}")
            result = manager.search(theme, candidate_count)
            unsent_books = filter_unsent_books(result.books, sent_records)
            selected_books = unsent_books[:book_count]
            if len(selected_books) >= book_count:
                selected_theme = theme
                break
            print(f"Not enough unsent books for theme: {theme}")

        if selected_theme is None:
            raise RuntimeError("Not enough unsent books found for any configured theme.")

        print(f"Selected theme: {selected_theme}")
        print("Selected books:")
        for index, book in enumerate(selected_books, start=1):
            print(f"{index}. {book.title}")

        prompt = build_summary_prompt(selected_books)
        summary = generate_summary(prompt, deepseek_config)
        cover_images = download_cover_images(selected_books)
        cover_cids = [image["cid"] if image else None for image in cover_images]
        html_body = build_book_email_html(selected_theme, selected_books, summary, cover_cids)
        print(summary)
        send_email(f"今日荐书：{selected_theme}", summary, html_body, cover_images)
        updated_records = append_sent_books(sent_records, selected_books, selected_theme)
        save_sent_books(updated_records)
    except ConfigError as exc:
        print(f"配置错误：{exc}")
        sys.exit(1)
    except SummaryGenerationError as exc:
        print(f"总结生成失败：{exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"程序运行失败：{exc}")
        sys.exit(1)

    print("Email sent successfully.")
    print("Sent history updated.")


if __name__ == "__main__":
    print_books()
