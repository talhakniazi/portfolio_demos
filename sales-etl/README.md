# Sales data pipeline (ETL) - portfolio demonstration

> **Self-initiated demonstration project.** Harbourline Supplies is a fictional catering-supplies wholesaler and all
> data is generated. This is not client work. It shows how a real monthly-reporting job would be automated.

**The problem it solves:** every month someone downloads the web-shop orders, the marketplace orders and the warehouse
stock sheet, pastes them into one spreadsheet, fixes the dates and prices by hand, removes duplicates, and builds the
same report. This pipeline does all of it in one command, in about a second, the same way every time.

```
 web shop CSV export ─┐
 marketplace REST API ├─► extract ─► clean & validate ─► SQLite warehouse ─► Excel report + email summary
 warehouse stock .xlsx┘                    │
                                           └─► rejected rows, each with the reason (nothing silently guessed)
```

## What it demonstrates

| Skill | Where |
|---|---|
| Reading messy CSV (4 date formats, `£`/`GBP` prices, blank lines, mixed-case SKUs) | `etl/extract.py`, `etl/transform.py` |
| REST API integration with pagination, timeouts and retry with backoff | `extract.marketplace_api` - the demo API fails once on purpose to show recovery |
| Excel input with a merged two-row header, found automatically | `extract.stock_sheet` |
| Validation that rejects rather than guesses, with a reason per row | `data/rejected/rejected_YYYY-MM.csv` |
| Duplicate removal and idempotent loading (re-running never double-counts) | `etl/load.py` (SQLite upserts) |
| Excel report with live formulas, charts, conditional formatting, frozen headers | `etl/report.py` |
| HTML summary ready to email | `reports/summary_YYYY-MM.html` |
| Logging and a run history table | `logs/pipeline.log`, `pipeline_runs` table |
| Automated tests, including recalculating the workbook in LibreOffice | `tests/` |

## Run it

```bash
pip install -r requirements.txt
python scripts/make_sample_data.py     # (re)creates the messy sample inputs in data/raw/
python demo.py                         # starts the mock marketplace API and runs October 2026
```

Expected output:

```
INFO    etl.extract: stock sheet 'Stock 31 Oct': header on row 4, 10 products
INFO    etl.extract: shop CSV: 176 rows (2 blank lines skipped)
WARNING etl.extract: API page 2 failed (HTTP 503), retry 1 in 0.5s
INFO    etl.extract: marketplace API: 80 orders over 4 pages
INFO    etl: loaded 332 sales lines, 5 rows rejected
INFO    etl: revenue £8475.22, 240 orders, 3 stock alerts
```

The 5 rejected rows are the problems planted in the sample data: a quantity written as "two", an impossible date
(31/13/2026), an unknown product code, and two orders exported twice.

Run the tests with `pip install pytest && python -m pytest`.

## Running it on a schedule

With a real API URL in `config.toml`, run `python -m etl.pipeline` (defaults to last month):

- **Linux/macOS (cron), 06:30 on the 1st of each month:**
  `30 6 1 * * cd /opt/sales-etl && .venv/bin/python -m etl.pipeline >> logs/cron.log 2>&1`
- **Windows Task Scheduler:** action `C:\sales-etl\.venv\Scripts\python.exe`, arguments `-m etl.pipeline`, start in `C:\sales-etl`.
- The exit code is non-zero on failure, so the scheduler (or a monitoring service) can alert someone.

## Adapting it for a client

Typical changes: point `config.toml` at the real files/API, add the API's authentication header in
`extract.marketplace_api`, map the client's column names in `transform.py`, and add or remove report sheets. The
validation rules and tests carry over unchanged.
