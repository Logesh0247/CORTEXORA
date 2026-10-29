import pandas as pd, pytest
from cortexora.analytics.metrics import enrich, kpis, marketing_metrics
from cortexora.models.forecasting import evaluate, weekly_series
from cortexora.monitoring.quality import run_all
from cortexora.decision_engine.engine import stockout_recommendations

@pytest.fixture
def tiny():
    orders = pd.DataFrame(dict(order_id=[1,2], customer_id=[1,1], order_date=["2024-01-01","2024-01-02"], region=["N","N"], channel=["Online","Online"]))
    items = pd.DataFrame(dict(order_id=[1,1,2], product_id=[1,2,1], qty=[2,1,1], unit_price=[100.,50.,100.], discount=[0.1,0.,0.], unit_cost=[50.,20.,50.]))
    return orders, items

def test_kpis_hand_calculated(tiny):
    k = kpis(enrich(*tiny)); assert k["revenue"] == pytest.approx(180+50+100); assert k["aov"] == pytest.approx(165)

def test_quality_flags_bad_qty():
    bad = pd.DataFrame(dict(order_id=[1], product_id=[1], qty=[0], unit_price=[10.]))
    assert (run_all({"order_items": bad}).status == "FAIL").any()

def test_forecast_evaluates_against_baseline():
    idx = pd.date_range("2023-01-01", periods=104, freq="W"); s = pd.Series(range(104), index=idx, dtype=float)
    r = evaluate(s); assert set(r) >= {"moving_average_4w","seasonal_naive"} and r["moving_average_4w"]["MAE"] >= 0

def test_stockout_detector():
    stock = pd.DataFrame(dict(product_id=[1], category=["Home"], stock_on_hand=[5], lead_time_days=[10], forecast_daily=[2.0], daily_sd=[1.0]))
    recs = stockout_recommendations(stock); assert recs and "Reorder" in recs[0]["action"]

def test_marketing_cac():
    m = pd.DataFrame(dict(channel=["Search"], spend=[100.], clicks=[100], conversions=[10]))
    assert marketing_metrics(m).cac_proxy.iloc[0] == 10
