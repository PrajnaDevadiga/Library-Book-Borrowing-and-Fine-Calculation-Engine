from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DATE_FORMAT = "%Y-%m-%d"
ALLOWED_BORROW_DAYS = 5
DEFAULT_FINE_PER_DAY = 20


@dataclass(frozen=True)
class Book:
    book_id: str
    book_name: str


@dataclass(frozen=True)
class FineRecord:
    record_id: str
    user_id: str
    book_id: str
    book_name: str
    borrow_date: str
    return_date: str
    borrow_days: int
    late_return: bool
    extra_days: int
    fine_amount: int


def _parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except (TypeError, ValueError):
        return None


def load_books(books_csv_path: str | Path) -> Dict[str, Book]:
    books: Dict[str, Book] = {}
    with open(books_csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            book_id = (row.get("book_id") or "").strip()
            if not book_id:
                continue
            books[book_id] = Book(
                book_id=book_id,
                book_name=(row.get("book_name") or "").strip(),
            )
    return books


def calculate_fine_records(
    books: Dict[str, Book],
    borrow_records_csv_path: str | Path,
    allowed_borrow_days: int = ALLOWED_BORROW_DAYS,
    fine_per_day: int = DEFAULT_FINE_PER_DAY,
) -> List[FineRecord]:
    fine_records: List[FineRecord] = []

    with open(borrow_records_csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            book_id = (row.get("book_id") or "").strip()
            book = books.get(book_id)
            if not book:
                continue

            borrow_date_raw = (row.get("borrow_date") or "").strip()
            return_date_raw = (row.get("return_date") or "").strip()

            borrow_date = _parse_date(borrow_date_raw)
            return_date = _parse_date(return_date_raw)
            if not borrow_date or not return_date:
                continue

            borrow_days = (return_date - borrow_date).days
            if borrow_days < 0:
                continue

            extra_days = max(0, borrow_days - allowed_borrow_days)
            fine_amount = extra_days * fine_per_day

            fine_records.append(
                FineRecord(
                    record_id=(row.get("record_id") or "").strip(),
                    user_id=(row.get("user_id") or "").strip(),
                    book_id=book_id,
                    book_name=book.book_name,
                    borrow_date=borrow_date_raw,
                    return_date=return_date_raw,
                    borrow_days=borrow_days,
                    late_return=extra_days > 0,
                    extra_days=extra_days,
                    fine_amount=fine_amount,
                )
            )

    return fine_records


def write_fine_report(fine_records: Iterable[FineRecord], output_path: str | Path) -> None:
    fieldnames = [
        "record_id",
        "user_id",
        "book_id",
        "book_name",
        "borrow_date",
        "return_date",
        "borrow_days",
        "late_return",
        "extra_days",
        "fine_amount",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in fine_records:
            writer.writerow(
                {
                    "record_id": record.record_id,
                    "user_id": record.user_id,
                    "book_id": record.book_id,
                    "book_name": record.book_name,
                    "borrow_date": record.borrow_date,
                    "return_date": record.return_date,
                    "borrow_days": record.borrow_days,
                    "late_return": "YES" if record.late_return else "NO",
                    "extra_days": record.extra_days,
                    "fine_amount": record.fine_amount,
                }
            )


def write_book_usage_summary(fine_records: Iterable[FineRecord], output_path: str | Path) -> None:
    usage = defaultdict(lambda: {"book_name": "", "borrow_count": 0, "late_returns": 0, "total_fine": 0})

    for record in fine_records:
        stats = usage[record.book_id]
        stats["book_name"] = record.book_name
        stats["borrow_count"] += 1
        stats["late_returns"] += int(record.late_return)
        stats["total_fine"] += record.fine_amount

    fieldnames = ["book_id", "book_name", "borrow_count", "late_returns", "total_fine"]
    with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for book_id in sorted(usage):
            stats = usage[book_id]
            writer.writerow(
                {
                    "book_id": book_id,
                    "book_name": stats["book_name"],
                    "borrow_count": stats["borrow_count"],
                    "late_returns": stats["late_returns"],
                    "total_fine": stats["total_fine"],
                }
            )


def process_library_data(
    books_csv_path: str | Path,
    borrow_records_csv_path: str | Path,
    fine_report_output_path: str | Path = "fine_report.csv",
    summary_output_path: str | Path = "book_usage_summary.csv",
) -> Tuple[List[FineRecord], Dict[str, Book]]:
    books = load_books(books_csv_path)
    fine_records = calculate_fine_records(books, borrow_records_csv_path)
    write_fine_report(fine_records, fine_report_output_path)
    write_book_usage_summary(fine_records, summary_output_path)
    return fine_records, books


if __name__ == "__main__":
    process_library_data("books.csv", "borrow_records.csv")
