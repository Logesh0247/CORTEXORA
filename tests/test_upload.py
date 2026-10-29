import pandas as pd, pytest
from cortexora.pipelines.upload import guess_mapping, transform
from cortexora.analytics.metrics import enrich, kpis

@pytest.fixture
def uci_like():
    return pd.DataFrame({
        "InvoiceNo": ["A1", "A1", "A2", "A3"], "StockCode": ["P1", "P2", "P1", "P1"],
        "Description": ["Mug", "Plate", "Mug", "Mug"], "Quantity": [2, 1, 3, -1],
        "InvoiceDate": ["2024-01-05", "2024-01-05", "2024-02-01", "bad-date"],
        "Price": [10.0, 20.0, 10.0, 10.0], "Customer ID": [7, 7, 8, 8], "Country": ["UK", "UK", "FR", "FR"]})

def test_guess_mapping_uci(uci_like):
    m = guess_mapping(list(uci_like.columns))
    assert m["order_date"] == "InvoiceDate" and m["qty"] == "Quantity" and m["unit_price"] == "Price" and m["product"] in ("Description", "StockCode")

def test_transform_counts_dropped_and_returns(uci_like):
    frames, rep = transform(uci_like, guess_mapping(list(uci_like.columns)), cost_ratio=0.5)
    assert rep["rows_in"] == 4 and rep["rows_dropped"] == 1 and rep["orders"] == 2
    k = kpis(enrich(frames["orders"], frames["order_items"]))
    assert k["revenue"] == pytest.approx(2*10 + 20 + 3*10)  # bad-date row excluded
    assert rep["cost_is_assumption"] and rep["cost_ratio"] == 0.5

def test_missing_required_mapping_raises(uci_like):
    m = guess_mapping(list(uci_like.columns)); m["unit_price"] = None
    with pytest.raises(ValueError, match="unit_price"): transform(uci_like, m)

def test_frames_match_warehouse_schema(uci_like):
    frames, _ = transform(uci_like, guess_mapping(list(uci_like.columns)))
    assert list(frames["orders"].columns) == ["order_id", "customer_id", "order_date", "region", "channel"]
    assert set(frames) == {"customers", "products", "orders", "order_items", "inventory_snapshots", "marketing_spend"}
