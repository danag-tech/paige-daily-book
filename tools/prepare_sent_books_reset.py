"""Prepare a one-time sent_books reset; never runs automatically."""

import argparse
import json
import shutil
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENT_BOOKS_PATH = PROJECT_ROOT / "sent_books.json"


def prepare_reset(apply: bool = False) -> Path:
    if not SENT_BOOKS_PATH.exists():
        raise FileNotFoundError(f"Missing {SENT_BOOKS_PATH}")

    backup_path = SENT_BOOKS_PATH.with_name(
        f"sent_books.backup.{date.today().isoformat()}.json"
    )
    if backup_path.exists():
        raise FileExistsError(f"Backup already exists: {backup_path}")

    with SENT_BOOKS_PATH.open("r", encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list):
        raise ValueError("sent_books.json must contain a JSON list")

    print(f"Records to back up: {len(records)}")
    print(f"Backup path: {backup_path}")
    if not apply:
        print("Dry preparation only. Re-run with --apply to create the backup and empty sent_books.json.")
        return backup_path

    shutil.copy2(SENT_BOOKS_PATH, backup_path)
    temporary_path = SENT_BOOKS_PATH.with_suffix(".reset.tmp")
    try:
        temporary_path.write_text("[]\n", encoding="utf-8")
        temporary_path.replace(SENT_BOOKS_PATH)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    print("Backup created and sent_books.json reset to an empty list.")
    return backup_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Create the backup and reset sent_books.json")
    args = parser.parse_args()
    prepare_reset(apply=args.apply)
