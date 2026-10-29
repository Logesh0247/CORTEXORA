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

def test_missing_date_or_value_raises(uci_like):
    m = guess_mapping(list(uci_like.columns)); m["order_date"] = None
    with pytest.raises(ValueError, match="date"): transform(uci_like, m)
    m = guess_mapping(list(uci_like.columns)); m["unit_price"] = None; m["revenue"] = None
    with pytest.raises(ValueError, match="price/total"): transform(uci_like, m)

def test_relaxed_mapping_still_transforms(uci_like):
    # no product/qty mapping -> honestly synthesised, and flagged in the report
    m = guess_mapping(list(uci_like.columns)); m["product"] = None; m["qty"] = None
    frames, rep = transform(uci_like, m)
    assert rep["product_is_fallback"] and rep["qty_is_assumed"]
    assert frames["order_items"]["qty"].sum() > 0

def test_frames_match_warehouse_schema(uci_like):
    frames, _ = transform(uci_like, guess_mapping(list(uci_like.columns)))
    assert list(frames["orders"].columns) == ["order_id", "customer_id", "order_date", "region", "channel"]
    assert set(frames) == {"customers", "products", "orders", "order_items", "inventory_snapshots", "marketing_spend"}


from cortexora.pipelines.upload import detect_mapping, profile_dataset, transform as _t

def test_detects_renamed_currency_columns():
    df = pd.DataFrame({
        "Order Date": ["01/03/2025", "15/03/2025", "02/04/2025"] * 4,
        "Item Name": ["Alpha", "Beta", "Alpha", "Gamma"] * 3,
        "Units Sold": [2, 1, 3, 5] * 3,
        "MRP": ["₹1,299.00", "₹899.50", "₹1,299.00", "₹2,499.00"] * 3,
    })
    det = detect_mapping(df)
    assert det["order_date"]["column"] == "Order Date"
    assert det["unit_price"]["column"] == "MRP"
    frames, rep = _t(df, {f: v["column"] for f, v in det.items()})
    assert rep["rows_used"] == 12 and rep["date_note"].startswith("day-first")

def test_revenue_only_aggregate_dataset():
    df = pd.DataFrame({"Month": pd.date_range("2024-01-01", periods=30, freq="MS").strftime("%Y-%m-%d"),
                       "Total Sales": [1000 + 37 * i for i in range(30)]})
    det = detect_mapping(df)
    assert det["order_date"]["column"] == "Month"
    frames, rep = _t(df, {f: v["column"] for f, v in det.items()})
    assert rep["price_is_derived"] and rep["qty_is_assumed"] and rep["product_is_fallback"]

def test_profile_generic_dataset():
    df = pd.DataFrame({"age": [25, 40, 33], "city": ["Salem", "Salem", "Erode"], "score": [1.5, 2.5, 3.5]})
    prof = profile_dataset(df, detect_mapping(df))
    assert prof["analysable_as_sales"] is False
    assert prof["dataset_type"] == "Generic tabular dataset"
    kinds = {c["column"]: c["kind"] for c in prof["columns"]}
    assert kinds == {"age": "numeric", "city": "text", "score": "numeric"}
