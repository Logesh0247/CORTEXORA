"""Weekly demand forecasting. Chronological split; seasonal-naive baseline; error metrics."""
import numpy as np, pandas as pd

def weekly_series(df: pd.DataFrame, category: str | None = None, products: pd.DataFrame | None = None) -> pd.Series:
    d = df
    if category and products is not None:
        d = d[d.product_id.isin(products.loc[products.category == category, "product_id"])]
    return d.set_index("order_date").resample("W")["qty"].sum().asfreq("W").fillna(0)

def evaluate(series: pd.Series, test_weeks: int = 12) -> dict:
    train, test = series.iloc[:-test_weeks], series.iloc[-test_weeks:]
    ma = train.rolling(4).mean().iloc[-1]
    fc_ma = pd.Series(ma, index=test.index)
    fc_sn = series.shift(52).reindex(test.index).fillna(train.iloc[-1])  # seasonal naive (52w), fallback last value
    def m(f): 
        e = test - f; return dict(MAE=float(e.abs().mean()), RMSE=float(np.sqrt((e**2).mean())), WAPE=float(e.abs().sum()/test.sum()) if test.sum() else float("nan"))
    return {"train_end": str(train.index.max().date()), "moving_average_4w": m(fc_ma), "seasonal_naive": m(fc_sn), "test_actual_total": float(test.sum())}

def forecast_next(series: pd.Series, horizon: int = 8) -> pd.DataFrame:
    ma = series.rolling(4).mean().iloc[-1]; sd = series.diff().std() or 0.0
    idx = pd.date_range(series.index.max() + pd.Timedelta(weeks=1), periods=horizon, freq="W")
    return pd.DataFrame(dict(week=idx, forecast=float(ma), lower=float(max(0, ma-1.28*sd)), upper=float(ma+1.28*sd)))  # ~80% interval, assumption stated

def rfm(orders: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    df = enrich_rfm(orders, items); ref = df.order_date.max()
    g = df.groupby("customer_id").agg(recency_days=("order_date", lambda s: (ref-s.max()).days), frequency=("order_id","nunique"), monetary=("revenue","sum")).reset_index()
    g["segment"] = pd.cut(g.recency_days, [-1,90,180,10**9], labels=["Active","At risk","Churned (heuristic)"])
    g["clv_simple"] = g.monetary / 2 * 3  # 24 months observed -> annualised x 3yr horizon, assumption in docs/03
    return g

def enrich_rfm(orders, items):
    from cortexora.analytics.metrics import enrich; return enrich(orders, items)
