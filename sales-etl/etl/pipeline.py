"""Run the whole pipeline:  python -m etl.pipeline --month 2026-10"""
from __future__ import annotations

import argparse
import logging
import sys
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from . import extract, load, report, transform

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("etl")


def setup_logging(logs_dir: Path):
    logs_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    for h in (logging.StreamHandler(sys.stdout), logging.FileHandler(logs_dir / "pipeline.log", encoding="utf-8")):
        h.setFormatter(fmt)
        root.addHandler(h)


def run(month: str, config: Path = ROOT / "config.toml", api_url: str | None = None) -> dict:
    cfg = tomllib.loads(config.read_text())
    P = lambda k: ROOT / cfg["outputs"][k]
    setup_logging(P("logs_dir"))
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log.info("=== run for %s ===", month)
    con = load.connect(P("database"))
    try:
        stock = transform.stock(extract.stock_sheet(ROOT / cfg["sources"]["stock_xlsx"]))
        catalogue = set(stock.sku)
        shop, bad1 = transform.shop(extract.shop_csv(ROOT / cfg["sources"]["shop_csv"]), catalogue)
        mk, bad2 = transform.marketplace(extract.marketplace_api(api_url or cfg["sources"]["marketplace_api"],
                                                                 cfg["sources"]["api_page_size"]), catalogue)
        sales = pd.concat([shop, mk], ignore_index=True)
        sales = sales[sales.order_date.map(lambda d: d.strftime("%Y-%m") == month)]
        rejected = pd.DataFrame(bad1 + bad2, columns=["source", "row", "id", "reason"])
        n = load.upsert_sales(con, sales)
        load.replace_stock(con, stock)
        log.info("loaded %d sales lines, %d rows rejected", n, len(rejected))
        rej_dir = P("rejected_dir"); rej_dir.mkdir(parents=True, exist_ok=True)
        rejected.to_csv(rej_dir / f"rejected_{month}.csv", index=False)

        s, st = report.month_data(con, month)
        parts = report.summarise(s, st, cfg["rules"]["low_stock_cover_days"])
        xlsx = report.excel(P("reports_dir") / f"Sales_Report_{month}.xlsx", month, *parts, rejected)
        kpi, by_product, _, _, _, alerts = parts
        htm = report.html_summary(P("reports_dir") / f"summary_{month}.html", month, kpi, by_product, alerts, len(rejected))
        log.info("report: %s", xlsx.relative_to(ROOT))
        log.info("revenue £%.2f, %d orders, %d stock alerts", kpi["Revenue"], kpi["Orders"], len(alerts))
        con.execute("INSERT INTO pipeline_runs (started_at, finished_at, month, rows_loaded, rows_rejected, status) VALUES (?,?,?,?,?,?)",
                    (started, datetime.now(timezone.utc).isoformat(timespec="seconds"), month, n, len(rejected), "ok"))
        con.commit()
        return {"loaded": n, "rejected": len(rejected), "kpi": kpi, "excel": xlsx, "html": htm, "alerts": len(alerts)}
    except Exception as e:
        log.exception("pipeline failed")
        con.execute("INSERT INTO pipeline_runs (started_at, finished_at, month, status, note) VALUES (?,?,?,?,?)",
                    (started, datetime.now(timezone.utc).isoformat(timespec="seconds"), month, "failed", str(e)[:500]))
        con.commit()
        raise
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="Harbourline Supplies monthly sales pipeline")
    last = (date.today().replace(day=1) - pd.Timedelta(days=1)).strftime("%Y-%m")
    ap.add_argument("--month", default=last, help="YYYY-MM (default: last month)")
    ap.add_argument("--api", help="override the marketplace API URL")
    a = ap.parse_args()
    try:
        r = run(a.month, api_url=a.api)
    except Exception:
        sys.exit(1)
    print(f"\nDone: {r['loaded']} lines loaded, {r['rejected']} rejected, report at {r['excel']}")


if __name__ == "__main__":
    main()
