"""Report: a formatted Excel workbook (with live formulas and a chart) plus an HTML summary for email."""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY, PALE = "1F3A5F", "E8EEF5"
HDR_FONT, HDR_FILL = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor=NAVY)
GBP, INT, PCT = '"£"#,##0.00', "#,##0", "0.0%"
THIN = Border(bottom=Side(style="thin", color="C9D3DF"))


def month_data(con, month: str):
    q = lambda sql, *a: pd.read_sql_query(sql, con, params=a)
    sales = q("""SELECT s.*, st.description, st.unit_cost FROM sales_lines s LEFT JOIN stock_snapshot st USING (sku)
                 WHERE substr(order_date, 1, 7) = ? ORDER BY order_date, order_id, line_no""", month)
    stock = q("SELECT * FROM stock_snapshot ORDER BY sku")
    return sales, stock


def summarise(sales: pd.DataFrame, stock: pd.DataFrame, cover_days: int):
    paid = sales[sales.status == "paid"].copy()
    paid["cost"] = paid.qty * paid.unit_cost
    days = max(1, pd.to_datetime(sales.order_date).dt.day.max() if len(sales) else 1)
    kpi = {"Revenue": paid.revenue.sum(), "Orders": paid.order_id.nunique(), "Units sold": int(paid.qty.sum()),
           "Average order value": paid.groupby("order_id").revenue.sum().mean() if len(paid) else 0,
           "Gross margin": (paid.revenue.sum() - paid.cost.sum()) / paid.revenue.sum() if paid.revenue.sum() else 0,
           "Refunded / cancelled lines": int((sales.status != "paid").sum())}
    by_product = (paid.groupby(["sku", "description"]).agg(units=("qty", "sum"), revenue=("revenue", "sum"), cost=("cost", "sum"))
                  .reset_index().sort_values("revenue", ascending=False))
    by_customer = (paid.groupby("customer").agg(orders=("order_id", "nunique"), revenue=("revenue", "sum"))
                   .reset_index().sort_values("revenue", ascending=False))
    by_channel = paid.groupby("channel").agg(orders=("order_id", "nunique"), revenue=("revenue", "sum")).reset_index()
    daily = paid.groupby("order_date").revenue.sum().reset_index()
    rate = paid.groupby("sku").qty.sum() / days
    st = stock.copy()
    st["daily_rate"] = st.sku.map(rate).fillna(0)
    st["days_cover"] = st.apply(lambda r: r.on_hand / r.daily_rate if r.daily_rate else float("inf"), axis=1)
    alerts = st[(st.on_hand <= st.reorder_at) | (st.days_cover < cover_days)].sort_values("days_cover")
    return kpi, by_product, by_customer, by_channel, daily, alerts


def _header(ws, row, headers, widths=None):
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        c.font, c.fill, c.alignment = HDR_FONT, HDR_FILL, Alignment(horizontal="center", vertical="center", wrap_text=True)
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = f"A{row + 1}"   # a string, so no empty cell is created below the header


def excel(path: Path, month: str, kpi, by_product, by_customer, by_channel, daily, alerts, rejected: pd.DataFrame):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = f"Harbourline Supplies - sales report {month}"
    ws["A1"].font = Font(bold=True, size=16, color=NAVY)
    ws["A2"] = "Demonstration data for a fictional company. Generated automatically by the sales pipeline."
    ws["A2"].font = Font(italic=True, color="666666")
    fmts = {"Revenue": GBP, "Average order value": GBP, "Gross margin": PCT}
    for i, (k, v) in enumerate(kpi.items(), start=4):
        ws.cell(row=i, column=1, value=k).font = Font(bold=True)
        c = ws.cell(row=i, column=2, value=float(v) if not isinstance(v, int) else v)
        c.number_format = fmts.get(k, INT)
        ws.cell(row=i, column=1).border = ws.cell(row=i, column=2).border = THIN
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 28, 16
    r0 = 12
    _header(ws, r0, ["Channel", "Orders", "Revenue", "Share"])
    ws.freeze_panes = None
    for i, row in enumerate(by_channel.itertuples(index=False), start=r0 + 1):
        ws.cell(row=i, column=1, value=row.channel)
        ws.cell(row=i, column=2, value=int(row.orders))
        ws.cell(row=i, column=3, value=float(row.revenue)).number_format = GBP
        last = r0 + len(by_channel)
        ws.cell(row=i, column=4, value=f"=C{i}/SUM($C${r0+1}:$C${last})").number_format = PCT   # live formula
    ws.column_dimensions["C"].width = ws.column_dimensions["D"].width = 14

    d = wb.create_sheet("Daily revenue")
    _header(d, 1, ["Date", "Revenue"], [14, 14])
    for row in daily.itertuples(index=False):
        d.append([pd.to_datetime(row.order_date).date(), float(row.revenue)])
        d.cell(row=d.max_row, column=1).number_format = "dd mmm"
        d.cell(row=d.max_row, column=2).number_format = GBP
    ch = LineChart(); ch.title = "Revenue per day"; ch.height, ch.width = 7.5, 18; ch.legend = None
    ch.add_data(Reference(d, min_col=2, min_row=1, max_row=d.max_row), titles_from_data=True)
    ch.set_categories(Reference(d, min_col=1, min_row=2, max_row=d.max_row))
    for s_ in ch.series:
        s_.smooth = False          # straight lines: daily figures shouldn't be drawn as a curve
    ws.add_chart(ch, "F4")

    p = wb.create_sheet("By product")
    _header(p, 1, ["SKU", "Product", "Units", "Revenue", "Cost", "Margin £", "Margin %"], [12, 30, 9, 13, 13, 13, 10])
    for i, row in enumerate(by_product.itertuples(index=False), start=2):
        p.append([row.sku, row.description, int(row.units), float(row.revenue), float(row.cost), f"=D{i}-E{i}", f"=IF(D{i}=0,0,F{i}/D{i})"])
        for col, f in ((4, GBP), (5, GBP), (6, GBP), (7, PCT)):
            p.cell(row=i, column=col).number_format = f
    n = p.max_row
    p.append(["Total", None, f"=SUM(C2:C{n})", f"=SUM(D2:D{n})", f"=SUM(E2:E{n})", f"=SUM(F2:F{n})", f"=IF(D{n+1}=0,0,F{n+1}/D{n+1})"])
    for col, f in ((3, INT), (4, GBP), (5, GBP), (6, GBP), (7, PCT)):
        p.cell(row=n + 1, column=col).number_format = f
    for c in p[n + 1]:
        c.font = Font(bold=True)
    bar = BarChart(); bar.type = "bar"; bar.title = "Revenue by product"; bar.height, bar.width = 8, 16; bar.legend = None
    bar.add_data(Reference(p, min_col=4, min_row=1, max_row=n), titles_from_data=True)
    bar.set_categories(Reference(p, min_col=2, min_row=2, max_row=n))
    p.add_chart(bar, "I2")

    c = wb.create_sheet("By customer")
    _header(c, 1, ["Customer", "Orders", "Revenue"], [28, 9, 13])
    for row in by_customer.itertuples(index=False):
        c.append([row.customer, int(row.orders), float(row.revenue)])
        c.cell(row=c.max_row, column=3).number_format = GBP

    a = wb.create_sheet("Stock alerts")
    _header(a, 1, ["SKU", "Product", "On hand", "Reorder at", "Sold per day", "Days of cover"], [12, 30, 10, 11, 12, 13])
    for row in alerts.itertuples(index=False):
        a.append([row.sku, row.description, int(row.on_hand), int(row.reorder_at), round(float(row.daily_rate), 2),
                  None if row.days_cover == float("inf") else round(float(row.days_cover), 1)])
    a.conditional_formatting.add(f"F2:F{max(2, a.max_row)}", CellIsRule(operator="lessThan", formula=["7"], fill=PatternFill("solid", fgColor="F8CBAD")))
    if a.max_row == 1:
        a.append(["No products below their reorder level."])

    j = wb.create_sheet("Rejected rows")
    _header(j, 1, ["Source", "Row", "Order", "Why it was rejected"], [16, 7, 14, 70])
    for row in rejected.itertuples(index=False):
        j.append([row.source, row.row, row.id, row.reason])
    if j.max_row == 1:
        j.append(["(none)"])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def html_summary(path: Path, month: str, kpi, by_product, alerts, n_rejected: int) -> Path:
    e = html.escape
    rows = "".join(f"<tr><td>{e(r.description)}</td><td align=right>{int(r.units)}</td><td align=right>£{r.revenue:,.2f}</td></tr>"
                   for r in by_product.head(5).itertuples(index=False))
    al = "".join(f"<li><b>{e(r.description)}</b>: {int(r.on_hand)} left"
                 + (f", about {r.days_cover:.0f} days of cover" if r.days_cover != float("inf") else "") + "</li>"
                 for r in alerts.itertuples(index=False)) or "<li>None</li>"
    body = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#1F3A5F;max-width:640px">
<h2>Sales report {e(month)}</h2>
<p><b>Revenue £{kpi['Revenue']:,.2f}</b> from {kpi['Orders']} orders (average £{kpi['Average order value']:,.2f}),
gross margin {kpi['Gross margin']:.1%}.</p>
<h3>Top products</h3><table cellpadding=4 style="border-collapse:collapse">{rows}</table>
<h3>Stock to reorder</h3><ul>{al}</ul>
<p>{n_rejected} source rows were set aside for checking (see the "Rejected rows" sheet).</p>
<p style="color:#777;font-size:12px">Demonstration data for a fictional company.</p></body></html>"""
    path.write_text(body, encoding="utf-8")
    return path
