import json
import sys
from pathlib import Path

from book_pool import POOL_REFILL_BATCH, POOL_TARGET_TOTAL, get_pool_books, get_pool_health, load_book_pool, rank_pool_candidates, refresh_book_pool, save_book_pool
from book_quality_filter import filter_quality_books
from config import ConfigError, get_deepseek_config
from cover_image import download_cover_images
from email_sender import send_email
from html_email_builder import build_book_email_html
from prompt_builder import build_summary_prompt
from providers.manager import ProviderManager
from sent_books import append_sent_books, build_book_keys, filter_unsent_books, load_sent_books, save_sent_books
from summary_generator import SummaryGenerationError, generate_summary_result
from theme_picker import get_ordered_themes, save_theme_history


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_books(dry_run: bool = False) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        deepseek_config = get_deepseek_config()
        app_config = load_config()
        book_count = app_config["book_count"]
        candidate_count = max(book_count * 3, 9)
        manager = ProviderManager(app_config)
        sent_records = load_sent_books()
        pool_records = load_book_pool()

        if not dry_run:
            pool_records = _replenish_book_pool(
                pool_records,
                manager,
                sent_records,
                candidate_count,
                list(app_config.get("theme_strategies", {}).keys()),
            )
        selected_theme = None
        selected_books = []
        discovered_books = []

        for theme in get_ordered_themes():
            print(f"Trying theme: {theme}")
            pool_candidates = filter_quality_books(get_pool_books(pool_records, theme), "book_pool")
            pool_books = filter_unsent_books(pool_candidates, sent_records)
            selected_books = pool_books[:book_count]
            if len(selected_books) >= book_count:
                selected_theme = theme
                discovered_books = []
                break

            try:
                result = manager.search(theme, candidate_count)
            except Exception as exc:
                print(f"Theme failed: {theme}: {exc}")
                continue

            quality_books = filter_quality_books(result.books, "provider")
            candidate_books = filter_unsent_books(quality_books, sent_records)
            combined_books = _unique_books(pool_books + candidate_books)
            selected_books = combined_books[:book_count]
            if len(selected_books) >= book_count:
                selected_theme = theme
                discovered_books = candidate_books
                break

            print(f"Not enough unsent books for theme: {theme}")

        if selected_theme is None:
            if not dry_run:
                save_book_pool(pool_records)
            raise RuntimeError("Not enough unsent books found for any configured theme after checking pool and fallback providers.")

        print(f"Selected theme: {selected_theme}")
        print("Selected books:")
        for index, book in enumerate(selected_books, start=1):
            print(f"{index}. {book.title}")

        prompt = build_summary_prompt(selected_books)
        generated_summary = generate_summary_result(prompt, deepseek_config)
        _apply_generated_summaries(selected_books, generated_summary.book_summaries)
        summary = generated_summary.daily_text
        cover_images = download_cover_images(selected_books)
        cover_cids = [image["cid"] if image else None for image in cover_images]
        html_body = build_book_email_html(selected_theme, selected_books, summary, cover_cids)
        print(summary)
        if dry_run:
            _write_dry_run_preview(html_body)
            print("Paige Daily Book Dry Run")
            print("Generated preview: archive/dry-run-email-preview.html")
            print("Skipped:")
            print("- email sending")
            print("- sent_books update")
            print("- book_pool update")
            print("- website update")
        else:
            send_email(f"今日荐书：{selected_theme}", summary, html_body, cover_images)
            save_theme_history(selected_theme)
            updated_records = append_sent_books(sent_records, selected_books, selected_theme)
            save_sent_books(updated_records)
            pool_records = refresh_book_pool(pool_records, selected_theme, discovered_books, updated_records, selected_books)
            save_book_pool(pool_records)
            _update_website_data_safely()
    except ConfigError as exc:
        print(f"配置错误：{exc}")
        sys.exit(1)
    except SummaryGenerationError as exc:
        print(f"总结生成失败：{exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"程序运行失败：{exc}")
        sys.exit(1)

    if not dry_run:
        print("Email sent successfully.")
        print("Sent history updated.")


def _replenish_book_pool(
    pool_records: list[dict],
    manager: ProviderManager,
    sent_records: list[dict],
    candidate_count: int,
    themes: list[str],
) -> list[dict]:
    before_count = len(pool_records)
    before_theme_counts = {theme: sum(1 for record in pool_records if record.get("theme") == theme) for theme in themes}
    health = get_pool_health(pool_records, themes)
    if health["total"] >= POOL_TARGET_TOTAL:
        return pool_records

    needed = POOL_TARGET_TOTAL - health["total"]
    candidates: list[tuple[str, object]] = []
    searched_topics: list[str] = []
    for theme in health["missing_themes"]:
        searched_topics.append(theme)
        try:
            result = manager.search(theme, candidate_count)
            quality_books = filter_quality_books(result.books, "provider")
            candidate_books = filter_unsent_books(quality_books, sent_records)
            candidates.extend((theme, book) for book in candidate_books)
        except Exception as exc:
            print(f"Pool replenishment failed for theme: {theme}: {exc}")
        if len(candidates) >= POOL_REFILL_BATCH:
            break

    selected_candidates = rank_pool_candidates(candidates)[:POOL_REFILL_BATCH]
    selected_by_theme: dict[str, list] = {}
    for theme, book in selected_candidates:
        selected_by_theme.setdefault(theme, []).append(book)

    for theme, discovered_books in selected_by_theme.items():
        try:
            pool_records = refresh_book_pool(
                pool_records,
                theme,
                discovered_books,
                sent_records,
                [],
            )
        except Exception as exc:
            print(f"Pool replenishment failed while saving theme {theme}: {exc}")

    after_count = len(pool_records)
    added_count = max(0, after_count - before_count)
    print("Pool refill:")
    print(f"Before: {before_count}")
    print(f"Need refill: {needed}")
    print(f"Added: {added_count}")
    print(f"After: {after_count}")
    print("Topics:")
    for theme in searched_topics:
        after_theme = sum(1 for record in pool_records if record.get("theme") == theme)
        print(f"- {theme}: +{max(0, after_theme - before_theme_counts.get(theme, 0))}")

    return pool_records

def _write_dry_run_preview(html_body: str) -> None:
    preview_path = Path(__file__).with_name("archive") / "dry-run-email-preview.html"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(html_body, encoding="utf-8")

def _apply_generated_summaries(books: list, summaries: list[str]) -> None:
    if len(summaries) < len(books):
        raise SummaryGenerationError("DeepSeek summary result does not include enough book summaries.")

    for book, summary in zip(books, summaries):
        book.summary = summary


def _update_website_data_safely() -> None:
    try:
        from generate_website_data import update_website_books

        update_website_books()
    except Exception as exc:
        print(f"Website data update failed: {exc}")

def _unique_books(books: list) -> list:
    unique_books = []
    seen_keys = set()
    for book in books:
        keys = build_book_keys(book)
        if not keys or keys & seen_keys:
            continue
        seen_keys.update(keys)
        unique_books.append(book)
    return unique_books


if __name__ == "__main__":
    print_books(dry_run="--dry-run" in sys.argv[1:])
