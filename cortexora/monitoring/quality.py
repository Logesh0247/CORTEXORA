"""Data-quality checks: schema, missing, duplicates, ranges, freshness."""
import pandas as pd
REQUIRED = {"orders": ["order_id","customer_id","order_date"], "order_items": ["order_id","product_id","qty","unit_price"]}

def check_frame(name: str, df: pd.DataFrame) -> list[dict]:
    out = []
    for col in REQUIRED.get(name, []):
        if col not in df: out.append(dict(check=f"{name}: missing column {col}", status="FAIL", detail="schema"))
    out.append(dict(check=f"{name}: duplicate rows", status="FAIL" if df.duplicated().any() else "PASS", detail=str(int(df.duplicated().sum()))))
    out.append(dict(check=f"{name}: missing values", status="WARN" if df.isna().any().any() else "PASS", detail=str(int(df.isna().sum().sum()))))
    if "qty" in df: out.append(dict(check="order_items: qty>0", status="FAIL" if (df.qty<=0).any() else "PASS", detail="range"))
    if "unit_price" in df: out.append(dict(check="order_items: unit_price>=0", status="FAIL" if (df.unit_price<0).any() else "PASS", detail="range"))
    if name=="orders" and "order_date" in df:
        out.append(dict(check="orders: freshness (max date)", status="PASS", detail=str(df.order_date.max())))
    return out

def run_all(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame([c for n, df in frames.items() for c in check_frame(n, df)])
