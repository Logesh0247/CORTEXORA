"""Customer churn prediction — validated classifier (Phase 4).

Business question: which previously-active customers will make *no* purchase
in the next ``label_window_days`` days, so retention effort can be prioritised?

Label definition (explicit, documented in docs/06_MODEL_CARD_CHURN.md):
  churn = 1 if a customer with >=1 order on/before ``cutoff`` has no order in
  (cutoff, cutoff + label_window_days].

Leakage rules enforced by construction:
  * Features are computed ONLY from orders on/before ``cutoff``.
  * The label uses ONLY orders after ``cutoff``.
  * ``build_dataset`` has a unit test proving post-cutoff orders cannot change
    any feature value.

Evaluation: stratified hold-out (customer-level, so the same customer never
appears in both sides), compared against a majority-class dummy baseline.
Metrics: precision, recall, F1, ROC-AUC, PR-AUC. Predictions are *risk
estimates from a model trained on synthetic demo data* — the UI labels them
as such until the model is retrained on real data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = [
    "recency_days", "frequency", "monetary", "avg_order_value",
    "avg_items_per_order", "avg_discount", "active_span_days",
    "orders_last_30d", "orders_last_90d", "tenure_days",
]


def build_dataset(orders: pd.DataFrame, items: pd.DataFrame,
                  cutoff: str | pd.Timestamp, label_window_days: int = 90) -> pd.DataFrame:
    """One row per customer active on/before cutoff, features + churn label."""
    from cortexora.analytics.metrics import enrich

    cutoff = pd.Timestamp(cutoff)
    df = enrich(orders, items)
    df["order_date"] = pd.to_datetime(df["order_date"])
    hist = df[df.order_date <= cutoff].copy()
    if hist.empty:
        return pd.DataFrame(columns=["customer_id", *FEATURES, "churn"])

    future_ids = set(df.loc[(df.order_date > cutoff)
                            & (df.order_date <= cutoff + pd.Timedelta(days=label_window_days)),
                            "customer_id"])

    rows = []
    for cid, g in hist.groupby("customer_id"):
        last, first = g.order_date.max(), g.order_date.min()
        per_order = g.groupby("order_id").agg(rev=("revenue", "sum"), n=("qty", "sum"))
        rows.append(dict(
            customer_id=int(cid),
            recency_days=(cutoff - last).days,
            frequency=int(g.order_id.nunique()),
            monetary=float(g.revenue.sum()),
            avg_order_value=float(per_order.rev.mean()),
            avg_items_per_order=float(per_order.n.mean()),
            avg_discount=float(g.discount.mean()),
            active_span_days=(last - first).days,
            orders_last_30d=int(g.loc[g.order_date > cutoff - pd.Timedelta(days=30), "order_id"].nunique()),
            orders_last_90d=int(g.loc[g.order_date > cutoff - pd.Timedelta(days=90), "order_id"].nunique()),
            tenure_days=(cutoff - first).days,
            churn=int(cid not in future_ids),
        ))
    return pd.DataFrame(rows)


def _metrics(y_true, y_pred, y_prob) -> dict:
    from sklearn.metrics import (average_precision_score, f1_score, precision_score,
                                 recall_score, roc_auc_score)
    out = dict(precision=float(precision_score(y_true, y_pred, zero_division=0)),
               recall=float(recall_score(y_true, y_pred, zero_division=0)),
               f1=float(f1_score(y_true, y_pred, zero_division=0)),
               roc_auc=float("nan"), pr_auc=float("nan"))
    if len(np.unique(y_true)) == 2:
        out["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        out["pr_auc"] = float(average_precision_score(y_true, y_prob))
    return out


def train_and_evaluate(data: pd.DataFrame, seed: int = 42) -> dict:
    """Train logistic regression vs dummy baseline; return metrics + fitted model."""
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if data["churn"].nunique() < 2 or len(data) < 30:
        raise ValueError(f"Insufficient data to train churn model: {len(data)} customers, "
                         f"churn classes present: {sorted(data['churn'].unique())}")

    X, y = data[FEATURES], data["churn"].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)

    candidates = {
        "baseline_majority": DummyClassifier(strategy="most_frequent"),
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "random_forest": RandomForestClassifier(n_estimators=200, random_state=seed, n_jobs=-1),
    }
    results, fitted = {}, {}
    for name, model in candidates.items():
        model.fit(Xtr, ytr)
        prob = model.predict_proba(Xte)[:, 1]
        results[name] = _metrics(yte, model.predict(Xte), prob)
        fitted[name] = model

    best_name = max((n for n in results if n != "baseline_majority"), key=lambda n: results[n]["pr_auc"])
    best = fitted[best_name]
    if hasattr(best, "named_steps") and "logisticregression" in best.named_steps:
        importance = dict(sorted(zip(FEATURES, np.abs(best.named_steps["logisticregression"].coef_[0])),
                                 key=lambda kv: -kv[1]))
        importance = {k: float(v) for k, v in importance.items()}
    else:
        importance = {k: float(v) for k, v in sorted(zip(FEATURES, best.feature_importances_),
                                                     key=lambda kv: -kv[1])}
    report = dict(n_customers=int(len(data)), churn_rate=float(y.mean()), test_size=int(len(yte)),
                  best_model=best_name, results=results, feature_importance=importance,
                  features=FEATURES, seed=seed)
    return {"report": report, "model": best, "test": (Xte, yte)}


def predict_risk(model, data: pd.DataFrame) -> pd.DataFrame:
    out = data[["customer_id", *FEATURES]].copy()
    out["churn_probability"] = model.predict_proba(data[FEATURES])[:, 1]
    out["risk_band"] = pd.cut(out.churn_probability, [-0.01, 0.33, 0.66, 1.01],
                              labels=["Low", "Medium", "High"])
    return out.sort_values("churn_probability", ascending=False)


def save_artifacts(result: dict, out_dir: Path) -> None:
    import joblib
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(result["model"], out_dir / "churn_model.joblib")
    (out_dir / "churn_evaluation.json").write_text(json.dumps(result["report"], indent=2))
