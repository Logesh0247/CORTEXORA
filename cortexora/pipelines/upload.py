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
    missing = [f for f in REQUIRED if not mapping.get(f)]
    if missing:
        raise ValueError(f"These required fields are not mapped: {missing}. Map them to columns in your file.")
    src = pd.DataFrame()
    src["order_date_raw"] = df[mapping["order_date"]]
    src["product_raw"] = df[mapping["product"]].astype(str)
    src["qty"] = pd.to_numeric(df[mapping["qty"]], errors="coerce")
    src["unit_price"] = pd.to_numeric(df[mapping["unit_price"]], errors="coerce")
    src["order_key"] = df[mapping["order_id"]].astype(str) if mapping.get("order_id") else [f"ROW{i}" for i in range(len(df))]
    src["customer_key"] = df[mapping["customer_id"]].astype(str) if mapping.get("customer_id") else "UNKNOWN"
    src["category"] = df[mapping["category"]].astype(str) if mapping.get("category") else "Uncategorised"
    src["region"] = df[mapping["region"]].astype(str) if mapping.get("region") else "Unknown"
    src["channel"] = df[mapping["channel"]].astype(str) if mapping.get("channel") else "Unknown"
    src["discount"] = pd.to_numeric(df[mapping["discount"]], errors="coerce").fillna(0) if mapping.get("discount") else 0.0
    if mapping.get("discount") and src["discount"].abs().max() > 1:  # given as percent
        src["discount"] = src["discount"] / 100
    src["order_date"] = pd.to_datetime(src["order_date_raw"], errors="coerce")
    cost_is_assumption = not mapping.get("unit_cost")
    src["unit_cost"] = (pd.to_numeric(df[mapping["unit_cost"]], errors="coerce") if mapping.get("unit_cost")
                        else src["unit_price"] * cost_ratio)

    n0 = len(src)
    bad = src["order_date"].isna() | src["qty"].isna() | src["unit_price"].isna() | (src["product_raw"].str.strip() == "")
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
    report = dict(rows_in=int(n0), rows_used=int(len(src)), rows_dropped=dropped,
                  returns_rows=int((src.qty < 0).sum()), cost_is_assumption=cost_is_assumption,
                  cost_ratio=cost_ratio if cost_is_assumption else None,
                  date_min=str(src.order_date.min().date()), date_max=str(src.order_date.max().date()),
                  orders=int(len(orders)), products=int(len(products)), customers=int(src.customer_id.nunique()))
    return frames, report
