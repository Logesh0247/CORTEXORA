import numpy as np, pandas as pd, pytest
from cortexora.analytics.experiments import ab_conversion, ab_continuous, required_sample_size, srm_check, diff_in_diff, mmm_readiness
from cortexora.analytics.competitor import validate_snapshots, price_gaps

def test_ab_known_effect():
    r = ab_conversion(1000, 150, 1000, 100)
    assert r["rate_treat"] == 0.15 and r["abs_effect"] == pytest.approx(0.05) and r["significant"] and r["ci_low"] > 0

def test_ab_null_not_significant():
    assert not ab_conversion(500, 50, 500, 52)["significant"]

def test_ab_invalid_counts():
    with pytest.raises(ValueError): ab_conversion(100, 101, 100, 50)

def test_sample_size_increases_as_mde_shrinks():
    assert required_sample_size(0.10, 0.01) > required_sample_size(0.10, 0.03) > 0

def test_srm_detects_broken_randomisation():
    assert srm_check(900, 100)["srm_suspected"] and not srm_check(505, 495)["srm_suspected"]

def test_continuous_effect():
    rng = np.random.default_rng(1); r = ab_continuous(rng.normal(55, 10, 800), rng.normal(50, 10, 800))
    assert 3 < r["abs_effect"] < 7 and r["significant"]

def test_did_recovers_known_effect():
    rng = np.random.default_rng(0); rows = []
    for unit in range(60):
        tr = int(unit < 30); base = rng.normal(100, 5)
        for post in (0, 1): rows.append(dict(y=base + 10*post + (8 if tr and post else 0) + rng.normal(0, 2), treated=tr, post=post))
    r = diff_in_diff(pd.DataFrame(rows)); assert r["did_effect"] == pytest.approx(8, abs=1.5) and r["p_value"] < 0.01

def test_mmm_gate_blocks_without_revenue():
    mkt = pd.DataFrame(dict(spend_date=pd.date_range("2023-01-01", periods=60, freq="W").repeat(4),
                            channel=["A","B","C","D"]*60, spend=np.random.default_rng(0).uniform(200, 900, 240)))
    g = mmm_readiness(mkt); assert not g.set_index("Requirement").loc["Revenue outcome joinable to spend by week", "Met"]

def test_competitor_validation_and_gaps():
    snap = pd.DataFrame(dict(product_id=[1], competitor=["Rival"], competitor_price=[80.], observed_at=["2024-12-01"], source_url=["https://example.com/p1"]))
    prods = pd.DataFrame(dict(product_id=[1], product_name=["P1"], category=["A"], list_price=[100.]))
    g = price_gaps(validate_snapshots(snap, [1]), prods); assert g.gap_pct.iloc[0] == pytest.approx(-20.0) and bool(g.alert.iloc[0])
    with pytest.raises(ValueError): validate_snapshots(snap.drop(columns=["source_url"]), [1])
