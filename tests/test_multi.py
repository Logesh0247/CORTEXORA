"""Multi-file / multi-format ingestion: parsers, ZIP expansion, batch combine."""
import io, json, zipfile
import pandas as pd
import pytest
from cortexora.pipelines.multi import parse_tabular, expand_uploads, analyse_batch


def _sales_csv(n_days=200, seed=1):
    import random, datetime
    rnd = random.Random(seed)
    rows = ["date,product,qty,unit_price"]
    for i in range(n_days * 3):
        d = datetime.date(2024, 1, 1) + datetime.timedelta(days=rnd.randint(0, n_days))
        rows.append(f"{d.isoformat()},Widget,{rnd.randint(1,5)},{9.99}")
    return ("\n".join(rows)).encode()


def test_parse_csv_json_excel_parquet():
    df, fmt, _ = parse_tabular("a.csv", _sales_csv(10))
    assert fmt == "CSV" and len(df) == 30
    df, fmt, _ = parse_tabular("a.json", json.dumps([{"x": 1}, {"x": 2}]).encode())
    assert fmt == "JSON" and len(df) == 2
    buf = io.BytesIO(); pd.DataFrame({"x": [1, 2]}).to_excel(buf, index=False)
    df, fmt, note = parse_tabular("a.xlsx", buf.getvalue())
    assert fmt == "Excel" and len(df) == 2 and "sheet" in note
    buf = io.BytesIO(); pd.DataFrame({"x": [1, 2, 3]}).to_parquet(buf)
    df, fmt, _ = parse_tabular("a.parquet", buf.getvalue())
    assert fmt == "Parquet" and len(df) == 3


def test_parse_unsupported_and_oversize():
    with pytest.raises(ValueError, match="unsupported"):
        parse_tabular("a.png", b"123")
    with pytest.raises(ValueError, match="limit"):
        parse_tabular("a.csv", b"x" * (26 * 1024 * 1024))


def test_zip_expansion_and_batch_combines_sales():
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as z:
        z.writestr("inner/s1.csv", _sales_csv(200, seed=1))
    batch = analyse_batch([("s2.csv", _sales_csv(200, seed=2)), ("bundle.zip", zbuf.getvalue()),
                           ("pic.png", b"fake"), ("hr.csv", b"age,city\n30,Salem\n40,Erode\n")])
    statuses = {e["file"]: e["status"] for e in batch["per_file"]}
    assert statuses["pic.png"] == "error"           # bad member reported, batch survives
    assert statuses["s1.csv"] == "ok"               # ZIP member ingested
    assert batch["combined"]["files_combined"] == 2
    assert batch["combined"]["kpis"]["revenue"] > 0
    kinds = {e["file"]: (e.get("result") or {}).get("kind") for e in batch["per_file"]}
    assert kinds["hr.csv"] == "generic"


def test_frames_from_lines_builds_warehouse():
    from cortexora.pipelines.multi import frames_from_lines, sales_lines
    import pandas as pd
    raw = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "product": ["A", "B"],
                        "qty": [2, 3], "unit_price": [10.0, 5.0], "customer_id": ["X", "Y"]})
    d, _rep, _det = sales_lines(raw)
    d["source_file"] = "f.csv"; d["product_key"] = d["product_name"].astype(str)
    frames = frames_from_lines(d)
    assert set(frames) == {"customers", "products", "orders", "order_items", "inventory_snapshots", "marketing_spend"}
    assert len(frames["products"]) == 2 and frames["inventory_snapshots"]["stock_on_hand"].eq(0).all()
    assert (frames["order_items"]["qty"] > 0).all()
