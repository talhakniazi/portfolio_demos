"""Load: idempotent upserts into SQLite, so re-running a month never double-counts."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales_lines (
  order_id TEXT NOT NULL, line_no INTEGER NOT NULL, channel TEXT NOT NULL, order_date TEXT NOT NULL,
  customer TEXT NOT NULL, sku TEXT NOT NULL, qty INTEGER NOT NULL CHECK (qty > 0),
  unit_price REAL NOT NULL, revenue REAL NOT NULL, status TEXT NOT NULL, loaded_at TEXT NOT NULL,
  PRIMARY KEY (order_id, line_no));
CREATE TABLE IF NOT EXISTS stock_snapshot (
  sku TEXT PRIMARY KEY, description TEXT, on_hand INTEGER, reorder_at INTEGER, unit_cost REAL, taken_at TEXT);
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, month TEXT, rows_loaded INTEGER, rows_rejected INTEGER, status TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS ix_sales_date ON sales_lines(order_date);
"""


def connect(path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def upsert_sales(con, df) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [(*r[:3], r[3].isoformat(), *r[4:], now) for r in df.itertuples(index=False)]
    con.executemany("""INSERT INTO sales_lines VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(order_id, line_no) DO UPDATE SET channel=excluded.channel, order_date=excluded.order_date,
        customer=excluded.customer, sku=excluded.sku, qty=excluded.qty, unit_price=excluded.unit_price,
        revenue=excluded.revenue, status=excluded.status, loaded_at=excluded.loaded_at""", rows)
    con.commit()
    return len(rows)


def replace_stock(con, df):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute("DELETE FROM stock_snapshot")
    con.executemany("INSERT INTO stock_snapshot VALUES (?,?,?,?,?,?)", [(*r, now) for r in df.itertuples(index=False)])
    con.commit()
