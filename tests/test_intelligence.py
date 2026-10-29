"""Five-stage post-upload intelligence: understand/discover/predict/test/recommend."""
import datetime, random
import pandas as pd
from cortexora.pipelines.multi import analyse_batch


def _declining_csv() -> bytes:
    rnd = random.Random(11)
    rows, start = [], datetime.date(2024, 1, 1)
    for w in range(40):
        for _ in range(10):
            d = start + datetime.timedelta(days=w * 7 + rnd.randint(0, 6))
            recent = w >= 20
            rows.append(dict(date=d.isoformat(), product="Loser", qty=8 if recent else 3,
                             unit_price=10.0, unit_cost=9.5, discount=0.35 if recent else 0.05,
                             customer=f"C{rnd.randint(1, 15)}"))
            rows.append(dict(date=d.isoformat(), product="Winner", qty=10 if recent else 5,
                             unit_price=30.0, unit_cost=12.0, discount=0.0,
                             customer=f"C{rnd.randint(16, 40)}"))
    buf = pd.DataFrame(rows)
    return buf.to_csv(index=False).encode()


def test_five_stages_on_uploaded_data():
    out = analyse_batch([("decline.csv", _declining_csv())])
    intel = out["combined"]["intelligence"]
    assert set(intel) >= {"understand", "discover", "predict", "test_decisions", "recommendations"}

    poor = {p["product_name"] for p in intel["understand"]["poor_performers"]}
    assert "Loser" in poor  # negative-margin product detected from the upload itself

    drivers = intel["discover"]["profit_drivers_products"]
    assert drivers[0]["name"] == "Loser" and drivers[0]["profit_delta"] < 0

    pred = intel["predict"]
    assert pred["forecast"]["available"] is True           # 40 weekly periods
    assert pred["stockout_risk"]["available"] is False     # no stock column -> honest refusal
    assert "heuristic" in pred["churn_risk"]["method"]

    names = [s["name"] for s in intel["test_decisions"]["scenarios"]]
    assert any("Price +5%" in n for n in names) and any("marketing" in n.lower() for n in names)

    recs = intel["recommendations"]
    assert recs and recs[0]["action"].startswith("Fix or delist 'Loser'")
    assert all(r["evidence"] and r["measure"] for r in recs)
    assert [r["priority"] for r in recs] == sorted(r["priority"] for r in recs)
