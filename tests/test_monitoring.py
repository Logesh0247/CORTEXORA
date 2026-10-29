import numpy as np, pandas as pd, pytest
from cortexora.monitoring.drift import population_stability_index, drift_report, performance_comparison

rng = np.random.default_rng(0)
def test_psi_identical_is_near_zero():
    x = rng.normal(0, 1, 2000); assert population_stability_index(x, x.copy()) < 0.01

def test_psi_detects_large_shift():
    assert population_stability_index(rng.normal(0, 1, 2000), rng.normal(2, 1, 2000)) > 0.25

def test_psi_insufficient_data():
    assert np.isnan(population_stability_index([1, 2], [1, 2]))

def test_drift_report_orders_worst_first():
    ref = pd.DataFrame(dict(a=rng.normal(0, 1, 500), b=rng.normal(0, 1, 500)))
    cur = pd.DataFrame(dict(a=rng.normal(1.5, 1, 500), b=rng.normal(0, 1, 500)))
    r = drift_report(ref, cur, ["a", "b"]); assert r.feature.iloc[0] == "a" and r.status.iloc[0].startswith("significant")

def test_performance_comparison_flags_only_real_degradation():
    assert performance_comparison({"pr_auc": .90}, {"pr_auc": .80})["degraded"]
    assert not performance_comparison({"pr_auc": .90}, {"pr_auc": .88})["degraded"]
    assert performance_comparison({"pr_auc": .90}, {})["degraded"] is None  # unlabelled -> no claim

def test_etl_preserves_decisions_and_logs_run(tmp_path):
    import sqlite3
    from cortexora.pipelines.etl import run
    src = tmp_path / "src"; src.mkdir()
    frames = dict(customers=pd.DataFrame(dict(customer_id=[1], segment=["A"], region=["N"], signup_date=["2022-01-01"])),
                  products=pd.DataFrame(dict(product_id=[1], product_name=["P"], category=["A"], unit_cost=[1.], list_price=[2.])),
                  orders=pd.DataFrame(dict(order_id=[1], customer_id=[1], order_date=["2024-01-01"], region=["N"], channel=["Online"])),
                  order_items=pd.DataFrame(dict(order_id=[1], product_id=[1], qty=[1], unit_price=[2.], discount=[0.], unit_cost=[1.])),
                  inventory_snapshots=pd.DataFrame(dict(product_id=[1], snapshot_date=["2024-01-01"], stock_on_hand=[5], lead_time_days=[3])),
                  marketing_spend=pd.DataFrame(dict(spend_date=["2024-01-01"], channel=["Search"], spend=[10.], clicks=[5], conversions=[1])))
    for n, df in frames.items(): df.to_csv(src / f"{n}.csv", index=False)
    db = tmp_path / "w.db"; run(src, db)
    with sqlite3.connect(db) as c: c.execute("INSERT INTO decisions(recommendation_id,status) VALUES ('REC-KEEP','approved')")
    run(src, db)  # rerun must not wipe the audit history
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT COUNT(*) FROM decisions WHERE recommendation_id='REC-KEEP'").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status='success'").fetchone()[0] == 2
