"""Single metric-definition layer (docs/03). All modules must use these functions."""
import pandas as pd

def enrich(orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    df = items.merge(orders, on="order_id", how="left", validate="many_to_one")
    df["revenue"] = df.qty * df.unit_price * (1 - df.discount)
    df["profit"] = df.revenue - df.qty * df.unit_cost
    df["order_date"] = pd.to_datetime(df.order_date)
    return df

def kpis(df: pd.DataFrame) -> dict:
    rev, prof = df.revenue.sum(), df.profit.sum()
    return dict(revenue=rev, profit=prof, margin=prof/rev if rev else 0.0,
                orders=df.order_id.nunique(), aov=rev/df.order_id.nunique() if df.order_id.nunique() else 0.0,
                units=int(df.qty.sum()), customers=df.customer_id.nunique())

def period_compare(df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    end = df.order_date.max(); cur = df[df.order_date > end - pd.Timedelta(days=days)]
    prev = df[(df.order_date <= end - pd.Timedelta(days=days)) & (df.order_date > end - pd.Timedelta(days=2*days))]
    a, b = kpis(cur), kpis(prev)
    return pd.DataFrame([dict(metric=k, current=a[k], previous=b[k], change_pct=(a[k]/b[k]-1)*100 if b[k] else float("nan")) for k in a])

def marketing_metrics(mkt: pd.DataFrame) -> pd.DataFrame:
    g = mkt.groupby("channel").agg(spend=("spend","sum"), clicks=("clicks","sum"), conversions=("conversions","sum")).reset_index()
    g["cac_proxy"] = g.spend / g.conversions.replace(0, pd.NA)
    g["conversion_rate"] = g.conversions / g.clicks.replace(0, pd.NA)
    return g  # no attributed-revenue join exists -> ROAS intentionally not computed (see docs/03)
