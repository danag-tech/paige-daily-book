import json
import sys
from pathlib import Path

from providers.manager import ProviderManager


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def print_books(theme: str) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    config = load_config()
    manager = ProviderManager(config)
    result = manager.search(theme, config["book_count"])

    print("今日主题：")
    print()
    print(theme)
    print()
    print("主题来源：")
    print()
    print(result.theme_source)
    print()
    print("书籍信息来源：")
    print()
    print(result.book_info_source)
    print()

    for index, book in enumerate(result.books, start=1):
        print(_number_label(index))
        print(f"书名：{book.title}")
        print(f"作者：{book.author}")
        print(f"ISBN：{book.isbn or '暂无 ISBN'}")
        print(f"评分：{book.rating or '暂无评分'}")
        print(f"封面 URL：{book.cover or '暂无封面'}")
        print(f"简介：{book.summary}")
        print()

    print("Provider 失败原因：")
    if result.failures:
        for failure in result.failures:
            print(f"- {failure}")
    else:
        print("无。")


def _number_label(index: int) -> str:
    labels = {1: "①", 2: "②", 3: "③"}
    return labels.get(index, str(index))


if __name__ == "__main__":
    theme = "认知升级"
    print_books(theme)
