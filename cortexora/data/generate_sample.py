"""Deterministic SYNTHETIC retail data (seed=42). Not real business data."""
import numpy as np, pandas as pd
from pathlib import Path

def generate(out: Path, seed: int = 42, months: int = 24) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    cats = {"Electronics": (80, 400), "Apparel": (20, 90), "Home": (30, 150), "Beauty": (10, 60)}
    products, pid = [], 0
    for c, (lo, hi) in cats.items():
        for j in range(5):
            pid += 1; price = round(float(rng.uniform(lo, hi)), 2)
            products.append(dict(product_id=pid, product_name=f"{c} Product {j+1}", category=c, unit_cost=round(price*0.55,2), list_price=price))
    products = pd.DataFrame(products)
    customers = pd.DataFrame(dict(customer_id=range(1, 501), segment=rng.choice(["Consumer","SMB","Enterprise"], 500, p=[.6,.3,.1]),
                                  region=rng.choice(["North","South","East","West"], 500), signup_date="2022-01-01"))
    dates = pd.date_range("2023-01-01", periods=months*30, freq="D")
    rows_o, rows_i, oid = [], [], 0
    for d in dates:
        seasonal = 1 + 0.3*np.sin(2*np.pi*d.dayofyear/365) + (0.25 if d.month == 12 else 0)
        for _ in range(max(1, int(rng.poisson(28*seasonal)))):
            oid += 1; cust = customers.sample(1, random_state=int(rng.integers(1e9))).iloc[0]
            rows_o.append(dict(order_id=oid, customer_id=int(cust.customer_id), order_date=d.date().isoformat(), region=cust.region, channel=rng.choice(["Online","Store","Marketplace"], p=[.55,.3,.15])))
            for p in products.sample(int(rng.integers(1,4)), random_state=int(rng.integers(1e9))).itertuples():
                rows_i.append(dict(order_id=oid, product_id=p.product_id, qty=int(rng.integers(1,5)), unit_price=p.list_price, discount=float(rng.choice([0,.05,.1,.2], p=[.6,.2,.15,.05])), unit_cost=p.unit_cost))
    orders, items = pd.DataFrame(rows_o), pd.DataFrame(rows_i)
    latest = orders.order_date.max()
    inv = pd.DataFrame([dict(product_id=p.product_id, snapshot_date=latest, stock_on_hand=int(rng.integers(5, 400)), lead_time_days=int(rng.integers(3,15))) for p in products.itertuples()])
    mkt_rows = [dict(spend_date=d.date().isoformat(), channel=ch, spend=round(float(rng.uniform(200,1500)),2), clicks=int(rng.integers(500,5000)), conversions=int(rng.integers(20,300)))
                for d in dates[::7] for ch in ["Search","Social","Email","Display"]]
    frames = dict(customers=customers, products=products, orders=orders, order_items=items, inventory_snapshots=inv, marketing_spend=pd.DataFrame(mkt_rows))
    out.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items(): df.to_csv(out / f"{name}.csv", index=False)
    return frames
if __name__ == "__main__":
    from cortexora.config import SAMPLE_DIR; generate(SAMPLE_DIR); print("synthetic sample data written to", SAMPLE_DIR)
