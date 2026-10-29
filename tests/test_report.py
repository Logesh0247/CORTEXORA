import pandas as pd
from cortexora.analytics.metrics import enrich
from cortexora.reports.report import generate_markdown_report

def test_report_contains_computed_values():
    orders = pd.DataFrame(dict(order_id=[1,2], customer_id=[1,2], order_date=["2024-12-01","2024-12-02"], region=["N","S"], channel=["Online","Online"]))
    items = pd.DataFrame(dict(order_id=[1,2], product_id=[1,1], qty=[1,1], unit_price=[100.,100.], discount=[0.,0.], unit_cost=[40.,40.]))
    df = enrich(orders, items)
    dec = pd.DataFrame(dict(recommendation_id=["R1"], status=["pending"], expected_impact=[10.], actual_outcome=[None], area=["Inventory"]))
    md = generate_markdown_report(df, None, None, dec, "test scope")
    assert "Revenue: $200" in md and "test scope" in md and "Pending recommendations awaiting review: 1" in md
    assert "does not invent results" in md
