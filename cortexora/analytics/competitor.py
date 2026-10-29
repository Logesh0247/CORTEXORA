"""Competitor Intelligence (Phase 6): validated manual/CSV snapshots only.
CORTEXORA has NO live competitor feed and never pretends to. Users supply
snapshots (public prices they collected compliantly, with source + timestamp);
we validate the schema, compare against our list prices, and flag gaps."""
from __future__ import annotations
import pandas as pd
COLUMNS = ["product_id", "competitor", "competitor_price", "observed_at", "source_url"]

def validate_snapshots(df: pd.DataFrame, product_ids) -> pd.DataFrame:
    missing = [c for c in COLUMNS if c not in df]
    if missing: raise ValueError(f"Missing required columns: {missing}")
    out = df[COLUMNS].copy()
    out["competitor_price"] = pd.to_numeric(out.competitor_price, errors="coerce")
    out["observed_at"] = pd.to_datetime(out.observed_at, errors="coerce")
    if out.competitor_price.isna().any() or (out.competitor_price <= 0).any():
        raise ValueError("competitor_price must be a positive number on every row.")
    if out.observed_at.isna().any(): raise ValueError("observed_at must be a valid date/timestamp on every row.")
    unknown = set(out.product_id) - set(product_ids)
    if unknown: raise ValueError(f"Unknown product_id values: {sorted(unknown)[:5]}")
    return out

def price_gaps(snap: pd.DataFrame, products: pd.DataFrame, alert_pct: float = 5.0) -> pd.DataFrame:
    g = snap.merge(products[["product_id", "product_name", "category", "list_price"]], on="product_id")
    g["gap_pct"] = (g.competitor_price / g.list_price - 1) * 100
    g["alert"] = g.gap_pct <= -alert_pct  # competitor undercuts us by >= alert_pct
    return g.sort_values("gap_pct")
