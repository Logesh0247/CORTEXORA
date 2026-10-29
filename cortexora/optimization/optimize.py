"""Business optimization (Phase 5). Every output is a *scenario* computed from
stated assumptions / fitted response curves — never a guaranteed outcome.
See docs/07_PHASE5_OPTIMIZATION.md for formulas and limitations."""
from __future__ import annotations
import numpy as np, pandas as pd

# ---------- Inventory: forecast-based reorder optimization ----------
def reorder_plan(stock: pd.DataFrame, review_days: int = 30, servicez: float = 1.65) -> pd.DataFrame:
    """stock columns: product_id, category, stock_on_hand, lead_time_days,
    forecast_daily, daily_sd, unit_cost.
    Target stock = demand over (lead+review) + safety stock (z~95% service level).
    expected_stockout_units_no_action = demand over lead time beyond stock."""
    s = stock.copy()
    horizon = s.lead_time_days + review_days
    s["safety_stock"] = servicez * s.daily_sd * np.sqrt(s.lead_time_days)
    s["target_stock"] = s.forecast_daily * horizon + s.safety_stock
    s["recommended_reorder_qty"] = np.ceil(np.clip(s.target_stock - s.stock_on_hand, 0, None)).astype(int)
    s["expected_stockout_units_no_action"] = np.clip(s.forecast_daily * s.lead_time_days - s.stock_on_hand, 0, None)
    s["estimated_order_cost"] = s.recommended_reorder_qty * s.get("unit_cost", 0)
    if "list_price" in s:  # margin $ at risk, so Decision Engine priorities compare like-for-like ($)
        s["margin_at_risk"] = s.expected_stockout_units_no_action * (s.list_price - s.unit_cost)
    s["stockout_risk"] = np.where(s.expected_stockout_units_no_action > 0, "High",
                                  np.where(s.stock_on_hand < s.forecast_daily * horizon, "Medium", "Low"))
    return s.sort_values("expected_stockout_units_no_action", ascending=False)

# ---------- Pricing: observed discount effectiveness ----------
def discount_effectiveness(df: pd.DataFrame) -> pd.DataFrame:
    """df = enriched order items. OBSERVED association only: discounted orders
    differ in many ways, so this does NOT estimate a causal discount effect."""
    d = df.copy()
    d["discount_bucket"] = pd.cut(d.discount, [-.001, 0, .09, .15, 1], labels=["0%", "5%", "10%", "20%+"])
    g = d.groupby("discount_bucket", observed=True).agg(
        line_items=("order_id", "size"), units=("qty", "sum"), revenue=("revenue", "sum"),
        profit=("profit", "sum"), avg_discount=("discount", "mean")).reset_index()
    g["margin"] = g.profit / g.revenue.replace(0, np.nan)
    g["revenue_share"] = g.revenue / g.revenue.sum()
    return g

def breakeven_units(fixed_cost: float, price: float, unit_cost: float) -> float:
    """Units needed to cover fixed_cost at (price - unit_cost) contribution each."""
    cm = price - unit_cost
    return float("inf") if cm <= 0 else fixed_cost / cm

# ---------- Marketing: response curves + constrained budget allocation ----------
def fit_response_curves(mkt: pd.DataFrame) -> pd.DataFrame:
    """Per channel fit log(conversions) = log(a) + b*log(spend) on weekly rows.
    b<1 implies diminishing returns. Reports R2; low-R2 channels are flagged
    and should not be trusted for allocation decisions."""
    out = []
    for ch, g in mkt.groupby("channel"):
        g = g[(g.spend > 0) & (g.conversions > 0)]
        if len(g) < 10: 
            out.append(dict(channel=ch, a=np.nan, b=np.nan, r2=np.nan, n=len(g), reliable=False)); continue
        x, y = np.log(g.spend), np.log(g.conversions)
        b, loga = np.polyfit(x, y, 1)
        pred = loga + b * x; ss = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        out.append(dict(channel=ch, a=float(np.exp(loga)), b=float(b), r2=float(ss), n=len(g),
                        reliable=bool(ss > 0.3 and 0 < b < 1.5)))
    return pd.DataFrame(out)

def expected_conversions(curves: pd.DataFrame, alloc: dict[str, float]) -> float:
    return float(sum(r.a * max(alloc.get(r.channel, 0.0), 0) ** r.b for r in curves.itertuples()))

def optimize_budget(mkt: pd.DataFrame, total_budget: float | None = None,
                    max_share: float = 0.6) -> dict:
    """Maximise sum a_c * spend_c^b_c  s.t. sum spend = budget, 0 <= spend_c <= max_share*budget.
    Uses only 'reliable' fitted channels; falls back to current shares if none fit."""
    from scipy.optimize import minimize
    curves = fit_response_curves(mkt)
    weekly = mkt.groupby("channel").spend.mean()
    budget = float(total_budget if total_budget is not None else weekly.sum())
    usable = curves[curves.reliable & curves.a.notna()]
    if usable.empty:
        alloc = (weekly / weekly.sum() * budget).to_dict()
        return dict(allocation=alloc, curves=curves, budget=budget, expected_gain_pct=0.0,
                    note="No reliable response curve (R2<=0.3 or implausible b) — keeping current allocation. More/varied spend data needed.")
    chans = list(usable.channel); current_raw = weekly.reindex(chans).fillna(0).to_dict()
    cur_total = sum(current_raw.values()) or 1.0
    # Compare at the SAME total budget: scale current shares up/down to `budget`.
    current = {c: v / cur_total * budget for c, v in current_raw.items()}
    x0 = np.array([current[c] for c in chans])
    neg = lambda x: -sum(r.a * max(xi, 0) ** r.b for xi, r in zip(x, usable.itertuples()))
    res = minimize(neg, x0, method="SLSQP", bounds=[(0, max_share * budget)] * len(chans),
                   constraints=[dict(type="eq", fun=lambda x: x.sum() - budget)])
    alloc = {c: float(v) for c, v in zip(chans, res.x)}
    cur_exp = sum(r.a * max(current[r.channel], 0) ** r.b for r in usable.itertuples())
    new_exp = -res.fun
    return dict(allocation=alloc, current_allocation=current, curves=curves, budget=budget,
                expected_current=float(cur_exp), expected_optimized=float(new_exp),
                expected_gain_pct=float(new_exp / cur_exp - 1) * 100 if cur_exp else 0.0,
                note="Expected values are model estimates from fitted curves on synthetic data — scenarios, not promises.")

def daily_demand_stats(df: pd.DataFrame, days: int = 90) -> pd.DataFrame:
    """Per-product daily demand mean/std over the trailing window (for reorder plans)."""
    end = df.order_date.max(); recent = df[df.order_date > end - pd.Timedelta(days=days)]
    daily = recent.groupby([recent.order_date.dt.normalize(), "product_id"]).qty.sum().reset_index()
    return daily.groupby("product_id").qty.agg(forecast_daily="mean", daily_sd="std").fillna(0).reset_index()
