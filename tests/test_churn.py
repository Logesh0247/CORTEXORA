import pandas as pd, pytest
from cortexora.models.churn import build_dataset, train_and_evaluate, FEATURES

@pytest.fixture
def data():
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    rows = []
    for i, d in enumerate(dates):
        for cid in range(1, 41):
            if cid > 20 and d > pd.Timestamp("2024-03-01"): continue  # half the customers churn away
            if (i + cid) % 5 == 0: rows.append(dict(order_id=len(rows)+1, customer_id=cid, order_date=d.date().isoformat(), region="N", channel="Online"))
    orders = pd.DataFrame(rows)
    items = pd.DataFrame([dict(order_id=o, product_id=1, qty=2, unit_price=50., discount=0., unit_cost=25.) for o in orders.order_id])
    return orders, items

def test_label_definition(data):
    ds = build_dataset(*data, cutoff="2024-04-01", label_window_days=30)
    assert set(ds.churn.unique()) <= {0, 1} and len(ds) == 40

def test_no_leakage_from_future_orders(data):
    orders, items = data
    base = build_dataset(orders, items, cutoff="2024-04-01", label_window_days=30).set_index("customer_id")
    future = pd.DataFrame([dict(order_id=9999, customer_id=21, order_date="2024-04-15", region="N", channel="Online")])
    o2 = pd.concat([orders, future], ignore_index=True)
    i2 = pd.concat([items, pd.DataFrame([dict(order_id=9999, product_id=1, qty=99, unit_price=999., discount=0., unit_cost=1.)])], ignore_index=True)
    after = build_dataset(o2, i2, cutoff="2024-04-01", label_window_days=30).set_index("customer_id")
    pd.testing.assert_frame_equal(base[FEATURES], after.loc[base.index, FEATURES])  # features unchanged
    assert base.loc[21, "churn"] == 1 and after.loc[21, "churn"] == 0  # only the label may change

def test_training_beats_or_matches_baseline_and_reports_metrics(data):
    ds = build_dataset(*data, cutoff="2024-04-01", label_window_days=60)
    rep = train_and_evaluate(ds)["report"]
    assert rep["best_model"] in ("logistic_regression", "random_forest")
    for m in rep["results"].values():
        assert 0 <= m["precision"] <= 1 and 0 <= m["f1"] <= 1
    assert rep["results"][rep["best_model"]]["pr_auc"] >= rep["results"]["baseline_majority"]["pr_auc"] - 1e-9
