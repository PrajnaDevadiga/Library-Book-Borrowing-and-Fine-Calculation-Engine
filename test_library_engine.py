import csv

from library_engine import (
    calculate_fine_records,
    load_books,
    process_library_data,
    write_book_usage_summary,
    write_fine_report,
)


def _write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        writer.writerows(rows)


def _record_by_id(records, record_id):
    return next(record for record in records if record.record_id == record_id)


def test_invalid_book_rejected():
    books = load_books("books.csv")
    records = calculate_fine_records(books, "borrow_records.csv")
    assert all(record.book_id != "B006" for record in records)


def test_invalid_date_ignored():
    books = load_books("books.csv")
    records = calculate_fine_records(books, "borrow_records.csv")
    assert all(record.record_id != "R006" for record in records)


def test_no_fine_within_due_date():
    books = load_books("books.csv")
    records = calculate_fine_records(books, "borrow_records.csv")
    r001 = _record_by_id(records, "R001")
    assert r001.fine_amount == 0
    assert r001.late_return is False


def test_fine_calculation():
    books = load_books("books.csv")
    records = calculate_fine_records(books, "borrow_records.csv")
    r002 = _record_by_id(records, "R002")
    assert r002.extra_days == 8
    assert r002.fine_amount == 160


def test_late_return_flag():
    books = load_books("books.csv")
    records = calculate_fine_records(books, "borrow_records.csv")
    r004 = _record_by_id(records, "R004")
    assert r004.late_return is True


def test_fine_report_output_contains_expected_columns(tmp_path):
    books = load_books("books.csv")
    records = calculate_fine_records(books, "borrow_records.csv")
    output_path = tmp_path / "fine_report.csv"

    write_fine_report(records, output_path)

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows
    assert set(rows[0].keys()) == {
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
    }
    assert any(row["late_return"] == "YES" for row in rows)


def test_book_usage_summary_aggregates_counts(tmp_path):
    books = load_books("books.csv")
    records = calculate_fine_records(books, "borrow_records.csv")
    output_path = tmp_path / "book_usage_summary.csv"

    write_book_usage_summary(records, output_path)

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        rows = {row["book_id"]: row for row in csv.DictReader(csv_file)}

    assert rows["B002"]["borrow_count"] == "2"
    assert rows["B002"]["late_returns"] == "2"
    assert rows["B002"]["total_fine"] == "400"


def test_process_library_data_generates_both_reports(tmp_path):
    fine_report = tmp_path / "fine_report.csv"
    summary_report = tmp_path / "book_usage_summary.csv"

    fine_records, books = process_library_data(
        "books.csv",
        "borrow_records.csv",
        fine_report_output_path=fine_report,
        summary_output_path=summary_report,
    )

    assert fine_report.exists()
    assert summary_report.exists()
    assert len(fine_records) > 0
    assert "B001" in books


def test_load_books_skips_blank_book_id(tmp_path):
    books_path = tmp_path / "books.csv"
    _write_csv(
        books_path,
        ["book_id", "book_name", "available_copies", "fine_per_day"],
        [
            ["B100", "Book A", 1, 10],
            ["", "Invalid Book", 1, 10],
        ],
    )

    books = load_books(books_path)

    assert "B100" in books
    assert "" not in books


def test_negative_borrow_duration_is_ignored(tmp_path):
    books_path = tmp_path / "books.csv"
    records_path = tmp_path / "borrow_records.csv"
    _write_csv(
        books_path,
        ["book_id", "book_name", "available_copies", "fine_per_day"],
        [["B200", "Book B", 1, 20]],
    )
    _write_csv(
        records_path,
        ["record_id", "user_id", "book_id", "borrow_date", "return_date"],
        [["RNEG", "U200", "B200", "2024-10-10", "2024-10-01"]],
    )

    books = load_books(books_path)
    records = calculate_fine_records(books, records_path)

    assert records == []


def test_custom_allowed_days_and_fine_per_day(tmp_path):
    books_path = tmp_path / "books.csv"
    records_path = tmp_path / "borrow_records.csv"
    _write_csv(
        books_path,
        ["book_id", "book_name", "available_copies", "fine_per_day"],
        [["B300", "Book C", 1, 99]],
    )
    _write_csv(
        records_path,
        ["record_id", "user_id", "book_id", "borrow_date", "return_date"],
        [["RCUS", "U300", "B300", "2024-10-01", "2024-10-07"]],
    )

    books = load_books(books_path)
    records = calculate_fine_records(books, records_path, allowed_borrow_days=3, fine_per_day=50)

    assert len(records) == 1
    assert records[0].extra_days == 3
    assert records[0].fine_amount == 150
