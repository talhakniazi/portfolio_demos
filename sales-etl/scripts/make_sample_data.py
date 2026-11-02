"""Generate the demo input files for Harbourline Supplies (a fictional company).

The files deliberately contain the problems real exports have: mixed date formats, currency symbols and
thousands separators, duplicate rows, blank lines, inconsistent SKU casing, a merged two-row Excel header,
refunds, and a few rows that are genuinely broken (so the pipeline must quarantine them, not guess).
Run:  python scripts/make_sample_data.py
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
rng = random.Random(42)

PRODUCTS = [  # sku, name, category, unit cost, list price
    ("HL-CUP-12", "Compostable cup 12oz (x50)", "Packaging", 3.10, 6.50),
    ("HL-CUP-08", "Compostable cup 8oz (x50)", "Packaging", 2.60, 5.40),
    ("HL-LID-12", "Sip lid 12oz (x50)", "Packaging", 1.20, 2.90),
    ("HL-BAG-KR", "Kraft carrier bag (x100)", "Packaging", 6.80, 13.90),
    ("HL-NAP-WH", "White napkins (x500)", "Tableware", 4.10, 8.75),
    ("HL-FRK-WD", "Wooden fork (x100)", "Tableware", 2.05, 4.60),
    ("HL-SPN-WD", "Wooden spoon (x100)", "Tableware", 2.05, 4.60),
    ("HL-GLV-NT", "Nitrile gloves L (x100)", "Hygiene", 3.90, 7.95),
    ("HL-SAN-5L", "Surface sanitiser 5L", "Hygiene", 7.40, 15.50),
    ("HL-ROL-TL", "Till rolls 57mm (x20)", "Office", 5.20, 10.80),
]
CUSTOMERS = ["Bean & Barrel Cafe", "Quayside Deli", "The Little Bakehouse", "Northgate Canteen", "Ferry Street Kitchen",
             "Pip's Pantry", "Harbour Fish Bar", "Greenleaf Juice Co", "Old Mill Tearoom", "Station Road Takeaway"]
START = date(2026, 10, 1)


def fmt_date(d: date, i: int) -> str:
    """Shop export mixes formats depending on which staff member exported it."""
    return [d.strftime("%d/%m/%Y"), d.isoformat(), d.strftime("%d %b %Y"), d.strftime("%d-%m-%y")][i % 4]


def money(x: float, i: int) -> str:
    return [f"£{x:,.2f}", f"{x:.2f}", f"GBP {x:,.2f}", f"£{x:.2f} "][i % 4]


def shop_csv():
    rows, n = [], 0
    for day in range(31):
        d = START + timedelta(days=day)
        for _ in range(rng.randint(3, 8)):
            n += 1
            sku, name, _, _, price = rng.choice(PRODUCTS)
            qty = rng.choice([1, 1, 2, 2, 3, 4, 6, 10])
            rows.append({"Order #": f"SH-{1000 + n}", "Order Date": fmt_date(d, n), "Customer": rng.choice(CUSTOMERS),
                         "SKU": sku.lower() if n % 7 == 0 else sku, "Item": name, "Qty": str(qty),
                         "Unit Price": money(price, n), "Status": "Refunded" if n % 23 == 0 else "Paid"})
    rows += [dict(rows[5]), dict(rows[40])]                     # duplicate exports
    rows.append({**rows[10], "Order #": "SH-9001", "Qty": "two"})          # broken quantity
    rows.append({**rows[11], "Order #": "SH-9002", "Order Date": "31/13/2026"})   # impossible date
    rows.append({**rows[12], "Order #": "SH-9003", "SKU": "HL-UNKNOWN"})   # SKU not in catalogue
    rng.shuffle(rows)
    with open(RAW / "shop_orders_export.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for i, r in enumerate(rows):
            w.writerow(r)
            if i in (30, 90):
                f.write(",,,,,,,\n")                           # blank lines from a spreadsheet save
    return len(rows)


def marketplace_json():
    """What the (mock) marketplace API returns, one list per page."""
    orders, n = [], 0
    for day in range(31):
        d = START + timedelta(days=day)
        for _ in range(rng.randint(1, 4)):
            n += 1
            lines = []
            for _ in range(rng.randint(1, 3)):
                sku, _, _, _, price = rng.choice(PRODUCTS)
                lines.append({"sku": sku, "quantity": rng.choice([1, 2, 5]), "unit_price_pence": int(round(price * 1.08 * 100))})
            orders.append({"id": f"MK-{50000 + n}", "created_at": f"{d.isoformat()}T{rng.randint(7, 21):02d}:{rng.randint(0, 59):02d}:00Z",
                           "buyer": {"company": rng.choice(CUSTOMERS + ["Seaview B&B", "Uni Catering Ltd"])},
                           "status": "cancelled" if n % 17 == 0 else "completed", "lines": lines})
    (RAW / "marketplace_orders.json").write_text(json.dumps(orders, indent=1))
    return len(orders)


def stock_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock 31 Oct"
    ws["A1"] = "HARBOURLINE SUPPLIES - WAREHOUSE STOCK"
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    ws.append(["Product", None, "Stock", None, "Costs"])        # two-row merged header, like a real stock sheet
    ws.merge_cells("A3:B3"); ws.merge_cells("C3:D3")
    ws.append(["SKU", "Description", "On hand", "Reorder at", "Unit cost (£)"])
    for c in ws[4]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDEBF7")
    for sku, name, _, cost, _ in PRODUCTS:
        ws.append([" " + sku + " " if sku.endswith("WD") else sku, name, rng.randint(0, 160), rng.choice([20, 30, 40]), cost])
    ws.append([])
    ws.append(["Notes: counted by J. Pike, see clipboard"])
    wb.save(RAW / "stock_levels.xlsx")


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    print("shop rows:", shop_csv())
    print("marketplace orders:", marketplace_json())
    stock_xlsx()
    print("stock sheet written")
