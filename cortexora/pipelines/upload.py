"""User dataset upload -> CORTEXORA data model (Upload & Analyse feature).

Accepts a single transactional CSV in *the user's* column names. We guess the
mapping from common synonyms, the user confirms it in the UI, and we transform
to the documented schema (docs/03). Honesty rules enforced in code:
  * Rows that fail parsing are dropped and *counted in the report* — never silently.
  * If the file has no cost column, profit/margin uses an explicit cost-ratio
    assumption chosen by the user and labelled as an estimate everywhere.
  * Negative quantities (returns in many retail files) are kept and reported —
    they reduce revenue, which is the correct treatment for returns data.
"""
from __future__ import annotations
import numpy as np, pandas as pd

SYNONYMS = {
    "order_date": ["order_date", "date", "invoicedate", "invoice_date", "orderdate", "transaction_date", "purchase_date", "day"],
    "order_id": ["order_id", "invoiceno", "invoice_no", "invoice", "orderid", "transaction_id", "bill_no"],
    "customer_id": ["customer_id", "customerid", "customer", "customer_no", "client_id", "user_id"],
    "product": ["product_name", "product", "description", "item", "item_name", "product_id", "stockcode", "sku", "productname"],
    "category": ["category", "cat", "product_category", "department", "type"],
    "qty": ["qty", "quantity", "units", "count", "quantity_ordered"],
    "unit_price": ["unit_price", "price", "unitprice", "rate", "sale_price", "amount_per_unit", "price_per_unit"],
    "discount": ["discount", "discount_pct", "discount_percent", "discount_rate"],
    "unit_cost": ["unit_cost", "cost", "cost_price", "purchase_price", "unitcost"],
    "region": ["region", "country", "state", "city", "location", "territory"],
    "channel": ["channel", "source", "sales_channel", "store_type", "platform"],
}
REQUIRED = ["order_date", "product", "qty", "unit_price"]

def guess_mapping(columns: list[str]) -> dict[str, str | None]:
    norm = {str(c).strip().lower().replace(" ", "_"): c for c in columns}
    out: dict[str, str | None] = {}
    for field, syns in SYNONYMS.items():
        out[field] = next((norm[s] for s in syns if s in norm), None)
    if out["order_id"] is None:  # every row can be its own order as a last resort
        out["order_id"] = None
    return out

def transform(df: pd.DataFrame, mapping: dict, cost_ratio: float = 0.55) -> tuple[dict, dict]:
    """mapping: field -> source column name (or None). Returns (frames, report).
    frames are the six CORTEXORA tables; report counts rows kept/dropped and notes."""
    # Flexible requirements: only a date and a value (price OR line total) are
    # truly required. Product and quantity can be honestly synthesised and the
    # report says so — any sales-shaped dataset can be analysed.
    if not mapping.get("order_date"):
        raise ValueError("No date column could be detected or mapped — trend and forecast need one.")
    if not mapping.get("unit_price") and not mapping.get("revenue"):
        raise ValueError("No price/total column could be detected or mapped — revenue analysis needs one.")
    src = pd.DataFrame()
    src["order_date_raw"] = df[mapping["order_date"]]
    product_is_fallback = not mapping.get("product")
    src["product_raw"] = (df[mapping["product"]].astype(str) if mapping.get("product")
                          else "All sales (no product column in file)")
    qty_is_assumed = not mapping.get("qty")
    src["qty"] = 1.0 if qty_is_assumed else _clean_num(df[mapping["qty"]])
    price_is_derived = False
    if mapping.get("unit_price") and not (mapping.get("revenue") and mapping["unit_price"] == mapping["revenue"]):
        src["unit_price"] = _clean_num(df[mapping["unit_price"]])
    else:  # line totals: derive unit price = total / qty (qty>=1 after assumption)
        price_is_derived = True
        totals = _clean_num(df[mapping.get("revenue") or mapping["unit_price"]])
        src["unit_price"] = totals / src["qty"].replace(0, np.nan)
    src["order_key"] = df[mapping["order_id"]].astype(str) if mapping.get("order_id") else [f"ROW{i}" for i in range(len(df))]
    src["customer_key"] = df[mapping["customer_id"]].astype(str) if mapping.get("customer_id") else "UNKNOWN"
    src["category"] = df[mapping["category"]].astype(str) if mapping.get("category") else "Uncategorised"
    src["region"] = df[mapping["region"]].astype(str) if mapping.get("region") else "Unknown"
    src["channel"] = df[mapping["channel"]].astype(str) if mapping.get("channel") else "Unknown"
    src["discount"] = _clean_num(df[mapping["discount"]]).fillna(0) if mapping.get("discount") else 0.0
    if mapping.get("discount") and src["discount"].abs().max() > 1:  # given as percent
        src["discount"] = src["discount"] / 100
    src["order_date"], date_note = parse_dates(src["order_date_raw"])
    cost_is_assumption = not mapping.get("unit_cost")
    src["unit_cost"] = (_clean_num(df[mapping["unit_cost"]]) if mapping.get("unit_cost")
                        else src["unit_price"] * cost_ratio)

    n0 = len(src)
    bad = src["order_date"].isna() | src["qty"].isna() | src["unit_price"].isna()
    if not product_is_fallback:
        bad = bad | (src["product_raw"].str.strip() == "") | (src["product_raw"].str.lower() == "nan")
    dropped = int(bad.sum()); src = src[~bad].copy()
    if src.empty:
        raise ValueError("No usable rows after parsing dates/quantities/prices. Check the column mapping and file contents.")
    if (src["unit_price"] < 0).any():
        raise ValueError("Negative unit prices found — fix the price column mapping (price should be per-unit, non-negative).")

    products = (src.groupby("product_raw").agg(category=("category", "first"),
                                               unit_cost=("unit_cost", "median"), list_price=("unit_price", "median"))
                  .reset_index().rename(columns={"product_raw": "product_name"}))
    products["product_id"] = range(1, len(products) + 1)
    customers = pd.DataFrame(dict(customer_key=sorted(src.customer_key.unique())))
    customers["customer_id"] = range(1, len(customers) + 1)
    customers["segment"], customers["region"] = "Uploaded", "Unknown"
    customers["signup_date"] = str(src.order_date.min().date())

    src = src.merge(products[["product_raw" if False else "product_name", "product_id"]], left_on="product_raw", right_on="product_name", how="left") \
             .merge(customers[["customer_key", "customer_id"]], on="customer_key", how="left")
    orders = (src.groupby("order_key").agg(customer_id=("customer_id", "first"), order_date=("order_date", "min"),
                                           region=("region", "first"), channel=("channel", "first")).reset_index())
    orders["order_id"] = range(1, len(orders) + 1)
    key2id = dict(zip(orders.order_key, orders.order_id))
    items = (src.assign(order_id=src.order_key.map(key2id))
               .groupby(["order_id", "product_id"]).agg(qty=("qty", "sum"), unit_price=("unit_price", "mean"),
                                                         discount=("discount", "mean"), unit_cost=("unit_cost", "mean")).reset_index())
    items["qty"] = items["qty"].round().astype(int)
    items = items[items.qty != 0]
    orders["order_date"] = orders.order_date.dt.date.astype(str)
    latest = orders.order_date.max()
    inv = pd.DataFrame(dict(product_id=products.product_id, snapshot_date=latest,
                            stock_on_hand=0, lead_time_days=7))  # unknown for uploaded data -> flagged in UI
    mkt = pd.DataFrame(columns=["spend_date", "channel", "spend", "clicks", "conversions"])
    frames = dict(customers=customers.drop(columns=["customer_key"])[["customer_id", "segment", "region", "signup_date"]],
                  products=products[["product_id", "product_name", "category", "unit_cost", "list_price"]],
                  orders=orders[["order_id", "customer_id", "order_date", "region", "channel"]],
                  order_items=items, inventory_snapshots=inv, marketing_spend=mkt)
    report = dict(qty_is_assumed=qty_is_assumed, price_is_derived=price_is_derived,
                  product_is_fallback=product_is_fallback, date_note=date_note,
                  rows_in=int(n0), rows_used=int(len(src)), rows_dropped=dropped,
                  returns_rows=int((src.qty < 0).sum()), cost_is_assumption=cost_is_assumption,
                  cost_ratio=cost_ratio if cost_is_assumption else None,
                  date_min=str(src.order_date.min().date()), date_max=str(src.order_date.max().date()),
                  orders=int(len(orders)), products=int(len(products)), customers=int(src.customer_id.nunique()))
    return frames, report

# =====================================================================
# Flexible detection & verification (any-dataset support)
# The functions above match *names*. The ones below also inspect the
# *contents* of each column, so files with arbitrary headers — renamed,
# localised, currency-formatted, aggregated, or not sales data at all —
# are verified, profiled and analysed as far as their structure honestly
# allows. Nothing is guessed silently: every inferred mapping records
# how it was detected and is surfaced in the verification report.
# =====================================================================
import re as _re

EXTRA_SYNONYMS = {
    "revenue": ["revenue", "total", "sales", "amount", "total_amount", "sales_amount", "turnover",
                "gmv", "net_sales", "gross_sales", "total_price", "line_total", "value", "income"],
    "order_date": ["timestamp", "datetime", "txn_date", "sale_date", "billing_date", "created_at", "when", "period", "month", "week", "year_month"],
    "qty": ["units_sold", "items", "items_sold", "no_of_items", "pieces", "volume", "sales_qty", "ordered_qty"],
    "unit_price": ["mrp", "selling_price", "sp", "price_inr", "price_usd", "unitpriceusd", "rate_per_unit"],
    "product": ["item_desc", "product_desc", "article", "goods", "merchandise", "stock_code", "itemcode", "product_code"],
    "customer_id": ["cust_id", "buyer", "buyer_id", "account_id", "member_id", "customer_code"],
    "category": ["segment", "product_line", "group", "class", "family", "genre"],
}

def _norm_header(c) -> str:
    return _re.sub(r"[^a-z0-9]", "", str(c).strip().lower())

def _clean_num(s: pd.Series) -> pd.Series:
    """Parse numbers written as humans write them: ₹1,299.00 / $1,299 / (42) / 12%."""
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    txt = (s.astype(str).str.replace(r"[₹$€£,\s]", "", regex=True)
             .str.replace(r"^\((.*)\)$", r"-\1", regex=True)
             .str.replace("%", "", regex=False))
    return pd.to_numeric(txt, errors="coerce")

def parse_dates(s: pd.Series):
    """Best-effort date parsing. Returns (datetime series, note). Handles ISO,
    dd/mm vs mm/dd (decided from unambiguous values), Excel serials, epochs."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce"), "already datetime"
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() > 0.9 and len(s):
        v = num.dropna()
        if v.between(20000, 90000).mean() > 0.9:
            return pd.to_datetime(v, unit="D", origin="1899-12-30", errors="coerce"), "Excel serial dates"
        if v.between(1e9, 2e9).mean() > 0.9:
            return pd.to_datetime(v, unit="s", errors="coerce"), "Unix epoch (seconds)"
        if v.between(1e12, 2e12).mean() > 0.9:
            return pd.to_datetime(v, unit="ms", errors="coerce"), "Unix epoch (ms)"
    txt = s.astype(str).str.strip()
    sample = txt[txt.str.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", na=False)]
    dayfirst, note = False, "ISO / unambiguous format"
    if len(sample):
        first = sample.str.extract(r"^(\d{1,2})[/-]")[0].astype(int)
        second = sample.str.extract(r"[/-](\d{1,2})[/-]")[0].astype(int)
        if (first > 12).any() and not (second > 12).any():
            dayfirst, note = True, "day-first (dd/mm) detected from values > 12 in first position"
        elif (second > 12).any() and not (first > 12).any():
            note = "month-first (mm/dd) detected from values > 12 in second position"
        else:
            note = "ambiguous dd/mm vs mm/dd — assumed month-first; check the reported date range"
    out = pd.to_datetime(txt, errors="coerce", dayfirst=dayfirst)
    if out.isna().mean() > 0.5:  # last resort: let pandas infer per-element
        alt = pd.to_datetime(txt, errors="coerce", format="mixed", dayfirst=dayfirst)
        if alt.notna().sum() > out.notna().sum():
            out = alt
    return out, note

def _col_kind(s: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(s): return "date"
    if pd.api.types.is_numeric_dtype(s): return "numeric"
    parsed, _ = parse_dates(s)
    if parsed.notna().mean() > 0.8: return "date"
    if _clean_num(s).notna().mean() > 0.8: return "numeric"
    return "text"

def detect_mapping(df: pd.DataFrame) -> dict:
    """Return {field: {column, confidence, how}} — name match first, then
    content-based inference. Never raises; unmapped fields get column=None."""
    cols = list(df.columns)
    norm = {_norm_header(c): c for c in cols}
    used: dict[str, dict] = {}
    syn = {f: SYNONYMS.get(f, []) + EXTRA_SYNONYMS.get(f, []) for f in
           list(SYNONYMS) + ["revenue"]}
    # 1) exact / contained name matches
    for field, names in syn.items():
        hit = None
        for n in names:
            if _norm_header(n) in norm: hit = norm[_norm_header(n)]; break
        if hit is None:  # token containment, e.g. "total_revenue_usd" ~ revenue
            for c in cols:
                nc = _norm_header(c)
                if any(_norm_header(n) and _norm_header(n) in nc for n in names):
                    hit = c; break
        if hit is not None:
            used[field] = {"column": hit, "confidence": "high", "how": "column-name match"}
    # 2) content-based inference for the essentials still missing
    kinds = {c: _col_kind(df[c]) for c in cols}
    taken = {v["column"] for v in used.values()}
    def free(kind=None):
        return [c for c in cols if c not in taken and (kind is None or kinds[c] == kind)]
    if "order_date" not in used:
        for c in free("date"):
            used["order_date"] = {"column": c, "confidence": "medium", "how": "values parse as dates"}; taken.add(c); break
    numeric_free = free("numeric")
    def _stats(c):
        v = _clean_num(df[c]).dropna()
        return v
    if "unit_price" not in used and "revenue" not in used:
        # a decimal, positive, price-like column
        for c in numeric_free:
            v = _stats(c)
            if len(v) and (v > 0).mean() > 0.9 and 0 < v.median() < 1e7:
                used["unit_price"] = {"column": c, "confidence": "medium", "how": "positive decimal values look like prices"}; taken.add(c); break
    if "qty" not in used:
        for c in [c for c in free("numeric")]:
            v = _stats(c)
            if len(v) and (v > 0).mean() > 0.9 and (v == v.round()).mean() > 0.9 and 0 < v.median() <= 100:
                used["qty"] = {"column": c, "confidence": "medium", "how": "small positive whole numbers look like quantities"}; taken.add(c); break
    if "product" not in used:
        for c in free("text"):
            u = df[c].nunique(dropna=True)
            if 1 < u <= max(50, len(df) // 2):
                used["product"] = {"column": c, "confidence": "medium", "how": "repeated text values look like products"}; taken.add(c); break
    if "category" not in used:
        for c in free("text"):
            u = df[c].nunique(dropna=True)
            if 1 < u <= 30:
                used["category"] = {"column": c, "confidence": "low", "how": "low-cardinality text looks like a category"}; taken.add(c); break
    if "customer_id" not in used:
        for c in free("text") + free("numeric"):
            u = df[c].nunique(dropna=True)
            if u > 10 and "product" in used and used["product"]["column"] != c:
                used["customer_id"] = {"column": c, "confidence": "low", "how": "many distinct values look like customer IDs"}; taken.add(c); break
    # derived price from a revenue/total column
    if "unit_price" not in used and "revenue" in used:
        used["unit_price"] = {"column": used["revenue"]["column"], "confidence": "medium",
                              "how": "derived: line total ÷ quantity (or per-row total if no quantity)"}
    for f in ["order_date", "product", "qty", "unit_price", "order_id", "customer_id", "category",
              "unit_cost", "discount", "region", "channel", "revenue"]:
        used.setdefault(f, {"column": None, "confidence": "none", "how": "not detected"})
    return used

def profile_dataset(df: pd.DataFrame, detected: dict | None = None) -> dict:
    """Structural verification of ANY tabular dataset."""
    detected = detected or detect_mapping(df)
    columns = []
    for c in df.columns:
        s = df[c]
        col = {"column": str(c), "kind": _col_kind(s),
               "non_null_pct": round(float(s.notna().mean() * 100), 1),
               "unique": int(s.nunique(dropna=True)),
               "sample": [str(x)[:40] for x in s.dropna().head(3).tolist()]}
        if col["kind"] == "numeric":
            v = _clean_num(s)
            col.update(min=float(v.min()) if v.notna().any() else None,
                       max=float(v.max()) if v.notna().any() else None)
        columns.append(col)
    role = {f: v for f, v in detected.items() if v["column"]}
    has_date = "order_date" in role
    has_measure = bool({"unit_price", "revenue"} & set(role))
    if has_date and has_measure and "product" in role:
        dtype_label = "Sales transactions" if "qty" in role else "Sales transactions (no quantity column)"
    elif has_date and has_measure:
        dtype_label = "Aggregated time series (date + value)"
    elif has_date:
        dtype_label = "Time-stamped records (no sales value detected)"
    else:
        dtype_label = "Generic tabular dataset"
    checks = [
        {"check": "Readable table", "status": "PASS", "detail": f"{len(df):,} rows × {len(df.columns)} columns"},
        {"check": "Date column", "status": "PASS" if has_date else "WARN",
         "detail": (f"{role['order_date']['column']} ({role['order_date']['how']})" if has_date else "none detected — trend & forecast unavailable")},
        {"check": "Sales value column", "status": "PASS" if has_measure else "WARN",
         "detail": ("detected" if has_measure else "none detected — revenue analysis unavailable")},
        {"check": "Product column", "status": "PASS" if "product" in role else "WARN",
         "detail": (str(role["product"]["column"]) if "product" in role else "not detected — analysed as one combined series")},
        {"check": "Missing cells", "status": "PASS" if df.isna().mean().mean() < 0.2 else "WARN",
         "detail": f"{df.isna().mean().mean() * 100:.1f}% of all cells empty"},
        {"check": "Duplicate rows", "status": "PASS" if df.duplicated().mean() < 0.05 else "WARN",
         "detail": f"{df.duplicated().mean() * 100:.1f}% exact duplicates"},
    ]
    return {"dataset_type": dtype_label, "columns": columns,
            "mapping": {f: v for f, v in detected.items()},
            "checks": checks,
            "analysable_as_sales": bool(has_date and has_measure),
            "analysable_as_timeseries": bool(has_date and any(c["kind"] == "numeric" for c in columns))}
