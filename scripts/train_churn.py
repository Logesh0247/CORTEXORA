"""Train + evaluate the churn model on current warehouse data; save artifacts.
Usage: .venv/bin/python scripts/train_churn.py"""
import sys; sys.path.insert(0, ".")
import pandas as pd
from pathlib import Path
from cortexora.pipelines.etl import load_table
from cortexora.models.churn import build_dataset, train_and_evaluate, save_artifacts

if __name__ == "__main__":
    orders, items = load_table("orders"), load_table("order_items")
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    cutoff = orders.order_date.max() - pd.Timedelta(days=90)  # label window needs 90d of future
    data = build_dataset(orders, items, cutoff)
    result = train_and_evaluate(data)
    out = Path("cortexora/models/artifacts"); save_artifacts(result, out)
    r = result["report"]
    print(f"customers={r['n_customers']} churn_rate={r['churn_rate']:.2%} best={r['best_model']}")
    for name, m in r["results"].items():
        print(f"  {name:22s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} ROC-AUC={m['roc_auc']:.3f} PR-AUC={m['pr_auc']:.3f}")
    print("artifacts ->", out)
