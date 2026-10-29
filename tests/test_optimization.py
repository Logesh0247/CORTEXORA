import numpy as np, pandas as pd, pytest
from cortexora.optimization.optimize import reorder_plan, discount_effectiveness, breakeven_units, fit_response_curves, optimize_budget

def test_reorder_zero_when_stocked_and_positive_when_short():
    stock = pd.DataFrame(dict(product_id=[1,2], category=["A","A"], stock_on_hand=[1000,5], lead_time_days=[7,7],
                              forecast_daily=[2.,2.], daily_sd=[1.,1.], unit_cost=[10.,10.]))
    p = reorder_plan(stock).set_index("product_id")
    assert p.loc[1,"recommended_reorder_qty"] == 0 and p.loc[2,"recommended_reorder_qty"] > 0
    assert p.loc[2,"stockout_risk"] == "High" and p.loc[2,"estimated_order_cost"] == p.loc[2,"recommended_reorder_qty"]*10

def test_safety_stock_increases_with_variability():
    base = dict(product_id=[1], category=["A"], stock_on_hand=[0], lead_time_days=[9], forecast_daily=[1.], unit_cost=[1.])
    lo = reorder_plan(pd.DataFrame({**base, "daily_sd":[0.]})); hi = reorder_plan(pd.DataFrame({**base, "daily_sd":[3.]}))
    assert hi.safety_stock.iloc[0] > lo.safety_stock.iloc[0] == 0

def test_breakeven():
    assert breakeven_units(1000, 50, 30) == 50 and breakeven_units(1000, 20, 30) == float("inf")

def test_discount_buckets():
    df = pd.DataFrame(dict(order_id=[1,2], qty=[1,1], discount=[0.,.2], revenue=[100.,80.], profit=[40.,4.]))
    g = discount_effectiveness(df); assert list(g.discount_bucket.astype(str)) == ["0%","20%+"]
    assert g.loc[g.discount_bucket.astype(str)=="20%+","margin"].iloc[0] == pytest.approx(0.05)

def test_budget_optimizer_respects_constraints_and_improves():
    rng = np.random.default_rng(0); rows=[]
    for w in range(60):
        for ch,a in [("Search",6.),("Display",1.8)]:
            s = rng.uniform(200,1500); rows.append(dict(spend_date=f"2024-01-{(w%28)+1:02d}", channel=ch, spend=s, clicks=100, conversions=max(1,int(a*s**0.55*rng.normal(1,.08)))))
    r = optimize_budget(pd.DataFrame(rows), total_budget=1000.)
    assert sum(r["allocation"].values()) == pytest.approx(1000., abs=1e-4)
    assert all(v <= 600.01 for v in r["allocation"].values())
    assert r["expected_gain_pct"] >= -0.01  # optimiser never worse than current on its own objective
    assert fit_response_curves(pd.DataFrame(rows)).reliable.all()
