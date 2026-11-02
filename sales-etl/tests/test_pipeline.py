import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from etl import transform  # noqa: E402


@pytest.mark.parametrize("raw,expected", [("03/04/2026", date(2026, 4, 3)), ("2026-10-09", date(2026, 10, 9)),
                                          ("9 Oct 2026", date(2026, 10, 9)), ("09-10-26", date(2026, 10, 9)),
                                          ("31/13/2026", None), ("", None)])
def test_dates_are_uk_day_first(raw, expected):
    assert transform.parse_date(raw) == expected


@pytest.mark.parametrize("raw,expected", [("£1,234.50", 1234.5), ("GBP 6.50", 6.5), ("£4.60 ", 4.6), ("4", 4.0), ("abc", None), ("-3", None)])
def test_money(raw, expected):
    assert transform.parse_money(raw) == expected


def test_quantities_must_be_whole_positive():
    assert transform.parse_qty("3") == 3 and transform.parse_qty("3.0") == 3
    assert transform.parse_qty("two") is None and transform.parse_qty("0") is None and transform.parse_qty("1.5") is None


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("run") / "proj"
    shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns("reports", "logs", "*.sqlite", "rejected", "__pycache__", ".pytest_cache"))
    out = subprocess.run([sys.executable, "demo.py"], cwd=d, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stdout + out.stderr
    return d, out.stdout


def test_end_to_end_counts(run_dir):
    d, out = run_dir
    assert "332 sales lines loaded, 5 rows set aside" in out
    assert "retry 1" in out, "the deliberate API failure was retried"
    rej = (d / "data/rejected/rejected_2026-10.csv").read_text()
    for reason in ("not a whole number", "not in the stock sheet", "unreadable date", "duplicate"):
        assert reason in rej


def test_rerun_does_not_double_count(run_dir):
    import sqlite3
    d, _ = run_dir
    before = sqlite3.connect(d / "data/warehouse.sqlite").execute("SELECT COUNT(*), SUM(revenue) FROM sales_lines").fetchone()
    subprocess.run([sys.executable, "demo.py"], cwd=d, capture_output=True, timeout=120, check=True)
    after = sqlite3.connect(d / "data/warehouse.sqlite").execute("SELECT COUNT(*), SUM(revenue) FROM sales_lines").fetchone()
    assert before == after


def test_excel_layout_and_totals_agree(run_dir):
    d, _ = run_dir
    wb = load_workbook(d / "reports/Sales_Report_2026-10.xlsx")
    for name in ("Summary", "Daily revenue", "By product", "By customer", "Stock alerts", "Rejected rows"):
        assert name in wb.sheetnames
    p = wb["By product"]
    assert p["A2"].value and p["A2"].value.startswith("HL-"), "data starts directly under the header"
    assert p["F2"].value == "=D2-E2"
    # The product revenue column must add up to the summary revenue
    total = sum(r[3] for r in p.iter_rows(min_row=2, max_row=p.max_row - 1, values_only=True))
    assert abs(total - wb["Summary"]["B4"].value) < 0.01


@pytest.mark.skipif(not shutil.which("soffice"), reason="LibreOffice not installed")
def test_formulas_recalculate_without_errors(run_dir, tmp_path):
    d, _ = run_dir
    subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", str(tmp_path), str(d / "reports/Sales_Report_2026-10.xlsx")],
                   capture_output=True, timeout=180, check=True)
    wb = load_workbook(tmp_path / "Sales_Report_2026-10.xlsx", data_only=True)
    errors = [(ws.title, c.coordinate) for ws in wb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("#")]
    assert errors == []
    p = wb["By product"]
    last = p.max_row
    revenue, cost, margin = p.cell(last, 4).value, p.cell(last, 5).value, p.cell(last, 6).value
    assert abs(margin - (revenue - cost)) < 0.01
    s = wb["Summary"]
    assert abs(s["B8"].value - margin / revenue) < 0.0005, "summary margin matches the product sheet"
