"""Extract: read each source exactly as it arrives. No cleaning here, so problems stay traceable to the source."""
from __future__ import annotations

import logging
import time

import pandas as pd
import requests
from openpyxl import load_workbook

log = logging.getLogger("etl.extract")


def shop_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df["_source"] = "shop_csv"
    df["_source_row"] = df.index + 2          # +2: header row and 1-based numbering, matches what you see in Excel
    blank = (df.drop(columns=["_source", "_source_row"]).apply(lambda c: c.str.strip()) == "").all(axis=1)
    log.info("shop CSV: %d rows (%d blank lines skipped)", (~blank).sum(), blank.sum())
    return df[~blank].reset_index(drop=True)


def marketplace_api(url: str, page_size: int = 25, retries: int = 4, session: requests.Session | None = None) -> list[dict]:
    """Page through the marketplace API, retrying temporary failures (429/5xx, timeouts) with backoff."""
    s = session or requests.Session()
    orders, page = [], 1
    while True:
        for attempt in range(1, retries + 1):
            try:
                r = s.get(url, params={"page": page, "per_page": page_size}, timeout=15)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
                r.raise_for_status()
                break
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if attempt == retries or (status and status < 500 and status != 429):
                    raise
                wait = 0.5 * 2 ** (attempt - 1)
                log.warning("API page %d failed (%s), retry %d in %.1fs", page, e, attempt, wait)
                time.sleep(wait)
        body = r.json()
        orders += body["data"]
        if not body.get("next_page"):
            break
        page = body["next_page"]
    log.info("marketplace API: %d orders over %d pages", len(orders), page)
    return orders


def stock_sheet(path) -> pd.DataFrame:
    """Find the real header row (the one containing 'SKU') instead of trusting a fixed row number."""
    ws = load_workbook(path, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r and any(str(c).strip().upper() == "SKU" for c in r if c is not None))
    cols = [str(c).strip() if c is not None else f"col{j}" for j, c in enumerate(rows[hdr])]
    data = [r for r in rows[hdr + 1:] if r and r[0] not in (None, "") and not str(r[0]).lower().startswith("notes")]
    df = pd.DataFrame(data, columns=cols)
    log.info("stock sheet '%s': header on row %d, %d products", ws.title, hdr + 1, len(df))
    return df
