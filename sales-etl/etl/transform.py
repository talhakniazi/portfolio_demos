"""Transform: one clean schema for every channel. Rows that can't be trusted are rejected with a reason, never guessed."""
from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd

DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d-%m-%y")   # UK day-first only: 03/04 is 3 April
SALES_COLUMNS = ["order_id", "line_no", "channel", "order_date", "customer", "sku", "qty", "unit_price", "revenue", "status"]


def parse_date(s: str) -> date | None:
    s = (s or "").strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def parse_money(s: str) -> float | None:
    s = re.sub(r"(?i)gbp|£|,|\s", "", str(s or ""))
    try:
        v = round(float(s), 2)
    except ValueError:
        return None
    return v if v >= 0 else None


def parse_qty(s) -> int | None:
    try:
        f = float(str(s).strip())
    except ValueError:
        return None
    return int(f) if f > 0 and f == int(f) else None


def norm_sku(s) -> str:
    return re.sub(r"\s+", "", str(s or "")).upper()


def shop(df: pd.DataFrame, catalogue: set[str]):
    good, bad = [], []
    for r in df.to_dict("records"):
        problems = []
        d = parse_date(r["Order Date"]);   d is None and problems.append(f"unreadable date '{r['Order Date']}'")
        q = parse_qty(r["Qty"]);           q is None and problems.append(f"quantity '{r['Qty']}' is not a whole number")
        p = parse_money(r["Unit Price"]);  p is None and problems.append(f"price '{r['Unit Price']}' is not an amount")
        sku = norm_sku(r["SKU"]);          sku not in catalogue and problems.append(f"SKU '{sku}' is not in the stock sheet")
        if problems:
            bad.append({"source": "shop_csv", "row": r["_source_row"], "id": r["Order #"], "reason": "; ".join(problems)})
            continue
        good.append({"order_id": r["Order #"].strip(), "line_no": 1, "channel": "Shop", "order_date": d,
                     "customer": r["Customer"].strip(), "sku": sku, "qty": q, "unit_price": p, "revenue": round(q * p, 2),
                     "status": "refunded" if r["Status"].strip().lower() == "refunded" else "paid"})
    out = pd.DataFrame(good, columns=SALES_COLUMNS)
    dupes = out.duplicated(subset=["order_id", "line_no"], keep="first")
    for oid in out.loc[dupes, "order_id"]:
        bad.append({"source": "shop_csv", "row": "", "id": oid, "reason": "duplicate of an earlier row (exported twice) - kept the first"})
    return out[~dupes].reset_index(drop=True), bad


def marketplace(orders: list[dict], catalogue: set[str]):
    good, bad = [], []
    for o in orders:
        try:
            d = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).date()
        except (KeyError, ValueError):
            bad.append({"source": "marketplace_api", "row": "", "id": o.get("id"), "reason": "missing or invalid created_at"})
            continue
        for n, line in enumerate(o.get("lines", []), start=1):
            sku = norm_sku(line.get("sku"))
            q, pence = line.get("quantity"), line.get("unit_price_pence")
            if sku not in catalogue or not isinstance(q, int) or q <= 0 or not isinstance(pence, int):
                bad.append({"source": "marketplace_api", "row": "", "id": f"{o['id']}/{n}", "reason": f"invalid line {line}"})
                continue
            price = pence / 100
            good.append({"order_id": o["id"], "line_no": n, "channel": "Marketplace", "order_date": d,
                         "customer": o.get("buyer", {}).get("company", "").strip() or "(not given)", "sku": sku, "qty": q,
                         "unit_price": price, "revenue": round(q * price, 2),
                         "status": "cancelled" if o.get("status") == "cancelled" else "paid"})
    return pd.DataFrame(good, columns=SALES_COLUMNS), bad


def stock(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"sku": df["SKU"].map(norm_sku), "description": df["Description"].astype(str).str.strip(),
                        "on_hand": pd.to_numeric(df["On hand"], errors="coerce").fillna(0).astype(int),
                        "reorder_at": pd.to_numeric(df["Reorder at"], errors="coerce").fillna(0).astype(int),
                        "unit_cost": pd.to_numeric(df["Unit cost (£)"], errors="coerce")})
    return out.drop_duplicates("sku")
