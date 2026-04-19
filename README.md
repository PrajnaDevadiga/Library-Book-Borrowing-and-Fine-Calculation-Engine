# Library Book Borrowing & Fine Calculation Engine

Python application to process library borrow records, validate data, calculate late return fines, and generate CSV reports.

## Objective

Given:
- `books.csv`
- `borrow_records.csv`

The engine validates records and applies business rules to produce:
1. `fine_report.csv`
2. `book_usage_summary.csv`

## Business Rules

- Book must exist in `books.csv`
- Borrow and return dates must be valid (`YYYY-MM-DD`)
- Allowed borrow duration: **5 days**
- Late fine formula: `extra_days * Rs.20`
- Fine per day: **Rs.20**

## Project Files

- `library_engine.py` - Core processing logic and report generation
- `test_library_engine.py` - Unit tests
- `pytest.ini` - Detailed pytest output + coverage enforcement
- `books.csv` - Book master data
- `borrow_records.csv` - Borrow transaction data

## Requirements

- Python 3.10+ (tested on Python 3.11)
- `pytest`
- `pytest-cov`

Install test dependencies:

```bash
python -m pip install pytest pytest-cov
```

## Run the Application

From the project folder:

```bash
python library_engine.py
```

This generates:
- `fine_report.csv`
- `book_usage_summary.csv`

## Run Tests (Detailed Report + Coverage)

```bash
python -m pytest
```
## Run Dashboard

```bash
streamlit run app.py
```

Configured behavior in `pytest.ini`:
- Verbose test output (`-vv -ra`)
- Coverage report with missing lines (`--cov-report=term-missing`)
- Coverage gate: fail if below **80%** (`--cov-fail-under=80`)

## Current Test Coverage

- Required coverage is **80% or above (>=80%)**.
- Current coverage is ~97%.

## Example Fine Logic

If `borrow_days = 13`:
- Allowed days = 5
- Extra days = 8
- Fine = `8 * 20 = Rs.160`

